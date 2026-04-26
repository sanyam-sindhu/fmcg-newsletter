import os
import json
import csv
import io
from pathlib import Path
from datetime import datetime, date as _date
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from state import NewsletterState, Article
from tools import (
    search_news, parse_raw_results, deduplicate,
    score_relevance, score_credibility, MARKETS,
)


def get_llm():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        load_dotenv(Path(__file__).parent / ".env", override=True)
        key = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(
        model="gpt-4o",
        max_tokens=4096,
        api_key=key,
    )


def node_search(state: NewsletterState) -> dict:
    market = state.get("market", "global")
    raw = search_news(market)
    articles = parse_raw_results(raw)
    return {
        "raw_articles": articles,
        "status": "searched",
        "messages": [AIMessage(content=f"Fetched {len(articles)} raw articles for market: {market}.")],
    }


def node_deduplicate(state: NewsletterState) -> dict:
    unique = deduplicate(state["raw_articles"])
    return {
        "deduplicated_articles": unique,
        "status": "deduplicated",
        "messages": [AIMessage(content=f"After dedup: {len(unique)} articles remain.")],
    }


def node_filter_relevance(state: NewsletterState) -> dict:
    scored = []
    for art in state["deduplicated_articles"]:
        art = dict(art)
        art["relevance_score"] = score_relevance(art["title"], art["content"])
        scored.append(art)
    filtered = [a for a in scored if a["relevance_score"] >= 0.15]
    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {
        "filtered_articles": filtered[:25],
        "status": "filtered",
        "messages": [AIMessage(content=f"Relevance filter kept {len(filtered[:25])} articles.")],
    }


def node_credibility_check(state: NewsletterState) -> dict:
    market = state.get("market", "global")
    checked = []
    for art in state["filtered_articles"]:
        art = dict(art)
        art["credibility_score"] = score_credibility(art["url"], market)
        checked.append(art)
    checked = [a for a in checked if a["credibility_score"] > 0.45]
    checked.sort(key=lambda x: x["credibility_score"], reverse=True)
    return {
        "credibility_checked_articles": checked,
        "status": "credibility_checked",
        "messages": [AIMessage(content=f"Credibility check passed {len(checked)} articles.")],
    }


def node_enrich(state: NewsletterState) -> dict:
    articles = state["credibility_checked_articles"]
    market = state.get("market", "global")
    market_label = MARKETS.get(market, {}).get("label", "Global")

    if not articles:
        return {"credibility_checked_articles": articles, "status": "enriched"}

    summaries = "\n\n".join([
        f"Article {i+1}:\nTitle: {a['title']}\nSource: {a['source']}\nContent: {a['content'][:500]}"
        for i, a in enumerate(articles[:15])
    ])

    prompt = f"""For each article below, extract:
1. deal_type: one of [Acquisition, Merger, Investment, IPO, Divestiture, Joint Venture, Unknown]
2. companies: list of company names involved (max 3)
3. deal_value: monetary value if mentioned, else ""
4. geography: primary country or region (e.g. India, USA, UK, Europe, Asia-Pacific, Global)

Market context: {market_label}

Return a JSON array: [{{"index": 1, "deal_type": "...", "companies": [...], "deal_value": "...", "geography": "..."}}]

{summaries}"""

    response = get_llm().invoke([HumanMessage(content=prompt)])
    try:
        text = response.content
        start = text.find("[")
        end = text.rfind("]") + 1
        enrichments = json.loads(text[start:end])
        for e in enrichments:
            idx = e["index"] - 1
            if 0 <= idx < len(articles):
                articles[idx] = dict(articles[idx])
                articles[idx]["deal_type"] = e.get("deal_type", "Unknown")
                articles[idx]["companies"] = e.get("companies", [])
                articles[idx]["deal_value"] = e.get("deal_value", "")
                articles[idx]["geography"] = e.get("geography", "")
    except Exception:
        pass

    return {
        "credibility_checked_articles": articles,
        "status": "enriched",
        "messages": [AIMessage(content="Enriched articles with deal metadata and geography.")],
    }


def node_generate_newsletter(state: NewsletterState) -> dict:
    articles = state["credibility_checked_articles"]
    market = state.get("market", "global")
    market_label = MARKETS.get(market, {}).get("label", "Global")
    as_of_date_raw = state.get("as_of_date") or datetime.now().strftime("%Y-%m-%d")
    try:
        parsed = _date.fromisoformat(as_of_date_raw)
        today = parsed.strftime("%B %d, %Y")
    except Exception:
        today = datetime.now().strftime("%B %d, %Y")

    if not articles:
        return {
            "newsletter_draft": "No relevant FMCG M&A articles found for this period.",
            "newsletter_sections": {},
            "status": "generated",
        }

    article_text = "\n\n".join([
        f"ARTICLE {i+1}:\nTitle: {a['title']}\nSource: {a['source']} | Date: {a['published_date']}\n"
        f"Deal Type: {a['deal_type']} | Companies: {', '.join(a['companies']) or 'see content'} | Value: {a['deal_value'] or 'undisclosed'} | Geography: {a.get('geography', '')}\n"
        f"Content: {a['content'][:900]}\nURL: {a['url']}"
        for i, a in enumerate(articles[:15])
    ])

    geo_instruction = (
        f"Focus specifically on {market_label} market deals. Group regional sub-markets if relevant."
        if market != "global"
        else "Cover global deal activity. Where geography is clear, note the region."
    )

    prompt = f"""You are a senior FMCG industry analyst writing a weekly M&A intelligence briefing for executives. Today is {today}. Market focus: {market_label}.

STRICT RULES:
- Use ONLY facts from the articles below. Do NOT generalise or invent.
- Name specific companies, brands, and deal values wherever the articles mention them.
- If a deal value is not mentioned, write "undisclosed".
- Each deal entry must name the ACQUIRER and TARGET. If only one party is named, say so.
- Avoid hollow phrases like "strategic rationale", "bolster capabilities", "evolving consumer preferences".
- Write like a Bloomberg brief — short, factual, dense with names and numbers.
- {geo_instruction}

FORMAT:

## EXECUTIVE SUMMARY
2–3 sentences. Name the most significant deals and dominant trend. Include actual company names and geographies.

## TOP DEALS THIS PERIOD
For each deal (up to 6):
**[Acquirer] acquired [Target]** | [Deal Type] | [Value or undisclosed]
- One sentence: what was announced and why it matters. Include country/region.
- Source: [source name]

## SECTOR BREAKDOWN
Group under: **Food & Beverage** / **Personal Care & Beauty** / **Household Products** / **Other**
Under each, list specific companies and deals from the articles.

## GEOGRAPHIC BREAKDOWN
Group deals by region/country found in the articles. Only include regions with actual deals.

## DEALS TO WATCH
2–3 bullets. Specific companies or situations from the articles worth tracking — include names and geography.

## MARKET OUTLOOK
2 sentences. Based strictly on patterns in these articles, what is the observable M&A direction in {market_label}?

---
ARTICLES:
{article_text}"""

    response = get_llm().invoke([HumanMessage(content=prompt)])
    newsletter = response.content

    sections_prompt = f"""Parse this newsletter into JSON:

{newsletter}

Return JSON:
{{"executive_summary": "...", "top_deals": [...], "sector_breakdown": {{}}, "geographic_breakdown": {{}}, "deals_to_watch": [...], "market_outlook": "..."}}"""

    sections_response = get_llm().invoke([HumanMessage(content=sections_prompt)])
    sections = {}
    try:
        text = sections_response.content
        start = text.find("{")
        end = text.rfind("}") + 1
        sections = json.loads(text[start:end])
    except Exception:
        sections = {"raw": newsletter}

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "title", "source", "url", "published_date",
        "deal_type", "companies", "deal_value", "geography",
        "relevance_score", "credibility_score",
    ])
    writer.writeheader()
    for a in articles:
        writer.writerow({
            "id": a["id"],
            "title": a["title"],
            "source": a["source"],
            "url": a["url"],
            "published_date": a["published_date"],
            "deal_type": a.get("deal_type", ""),
            "companies": "; ".join(a.get("companies", [])),
            "deal_value": a.get("deal_value", ""),
            "geography": a.get("geography", ""),
            "relevance_score": a["relevance_score"],
            "credibility_score": a["credibility_score"],
        })

    return {
        "newsletter_draft": newsletter,
        "newsletter_sections": sections,
        "csv_data": output.getvalue(),
        "status": "generated",
        "messages": [AIMessage(content="Newsletter generated.")],
    }


def build_graph(checkpointer: PostgresSaver) -> StateGraph:
    graph = StateGraph(NewsletterState)
    graph.add_node("search", node_search)
    graph.add_node("deduplicate", node_deduplicate)
    graph.add_node("filter_relevance", node_filter_relevance)
    graph.add_node("credibility_check", node_credibility_check)
    graph.add_node("enrich", node_enrich)
    graph.add_node("generate_newsletter", node_generate_newsletter)

    graph.set_entry_point("search")
    graph.add_edge("search", "deduplicate")
    graph.add_edge("deduplicate", "filter_relevance")
    graph.add_edge("filter_relevance", "credibility_check")
    graph.add_edge("credibility_check", "enrich")
    graph.add_edge("enrich", "generate_newsletter")
    graph.add_edge("generate_newsletter", END)

    return graph.compile(checkpointer=checkpointer)
