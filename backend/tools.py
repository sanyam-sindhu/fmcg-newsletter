import os
import hashlib
import re
from datetime import datetime
from typing import List
from tavily import TavilyClient
from state import Article


MARKETS = {
    "global":      {"label": "Global",       "geo_terms": [],                        "lang": "en"},
    "india":       {"label": "India",         "geo_terms": ["India", "Indian"],       "lang": "en"},
    "usa":         {"label": "USA",           "geo_terms": ["USA", "US", "America"],  "lang": "en"},
    "uk":          {"label": "UK",            "geo_terms": ["UK", "Britain"],         "lang": "en"},
    "europe":      {"label": "Europe",        "geo_terms": ["Europe", "European"],    "lang": "en"},
    "asia_pacific":{"label": "Asia-Pacific",  "geo_terms": ["Asia", "APAC", "Southeast Asia", "China", "Japan"], "lang": "en"},
}

MARKET_DOMAINS = {
    "global": {
        "reuters.com": 0.95, "bloomberg.com": 0.95, "ft.com": 0.92, "wsj.com": 0.92,
        "cnbc.com": 0.90, "forbes.com": 0.88, "businesswire.com": 0.88,
        "prnewswire.com": 0.85, "globenewswire.com": 0.85, "marketwatch.com": 0.84,
        "axios.com": 0.83, "entrepreneur.com": 0.82, "dealstreetasia.com": 0.82,
        "grocerygazette.co.uk": 0.80, "fooddive.com": 0.80, "foodbusinessnews.net": 0.80,
        "thegrocer.co.uk": 0.80, "just-food.com": 0.80, "beveragedaily.com": 0.78,
        "cosmeticsbusiness.com": 0.78, "capstonepartners.com": 0.76,
        "protisglobal.com": 0.72, "lplegal.com": 0.70, "hahnbeck.com": 0.70,
        "objectiveibv.com": 0.70, "roadmapadvisors.com": 0.68, "hl.com": 0.68,
        "digitaldefynd.com": 0.65,
    },
    "india": {
        "economictimes.indiatimes.com": 0.93, "livemint.com": 0.92,
        "business-standard.com": 0.92, "moneycontrol.com": 0.88,
        "financialexpress.com": 0.88, "hindubusinessline.com": 0.87,
        "vccircle.com": 0.86, "entrackr.com": 0.82, "inc42.com": 0.80,
        "dealstreetasia.com": 0.82, "reuters.com": 0.95, "bloomberg.com": 0.95,
        "businesswire.com": 0.88, "prnewswire.com": 0.85, "forbes.com": 0.85,
        "foodbusinessnews.net": 0.78, "fooddive.com": 0.78,
    },
    "usa": {
        "reuters.com": 0.95, "bloomberg.com": 0.95, "wsj.com": 0.93,
        "cnbc.com": 0.90, "forbes.com": 0.88, "businesswire.com": 0.88,
        "prnewswire.com": 0.85, "globenewswire.com": 0.85, "marketwatch.com": 0.84,
        "axios.com": 0.83, "fooddive.com": 0.82, "foodbusinessnews.net": 0.82,
        "grocerydive.com": 0.80, "supermarketnews.com": 0.80,
        "capstonepartners.com": 0.76, "protisglobal.com": 0.72,
    },
    "uk": {
        "ft.com": 0.95, "reuters.com": 0.95, "bloomberg.com": 0.93,
        "thegrocer.co.uk": 0.90, "grocerygazette.co.uk": 0.88,
        "businesswire.com": 0.85, "prnewswire.com": 0.85,
        "just-food.com": 0.82, "foodmanufacture.co.uk": 0.82,
        "cosmeticsbusiness.com": 0.80, "hahnbeck.com": 0.75,
        "lplegal.com": 0.72, "thisismoney.co.uk": 0.78,
    },
    "europe": {
        "reuters.com": 0.95, "bloomberg.com": 0.95, "ft.com": 0.93,
        "businesswire.com": 0.88, "prnewswire.com": 0.85,
        "just-food.com": 0.82, "foodbev.com": 0.80,
        "foodnavigator.com": 0.82, "cosmeticsbusiness.com": 0.80,
        "dealstreetasia.com": 0.78, "globalcosmeticsnews.com": 0.75,
    },
    "asia_pacific": {
        "dealstreetasia.com": 0.90, "reuters.com": 0.95, "bloomberg.com": 0.95,
        "businesswire.com": 0.88, "prnewswire.com": 0.85,
        "nikkei.com": 0.88, "scmp.com": 0.85, "straitstimes.com": 0.83,
        "livemint.com": 0.82, "economictimes.indiatimes.com": 0.82,
        "techcrunch.com": 0.78, "foodnavigator-asia.com": 0.82,
    },
}

SOCIAL_DOMAINS = {"linkedin.com", "twitter.com", "facebook.com", "reddit.com", "youtube.com", "instagram.com"}

FMCG_KEYWORDS = [
    "fmcg", "consumer goods", "food", "beverage", "drink", "snack",
    "personal care", "beauty", "cosmetic", "household", "cleaning",
    "packaged goods", "cpg", "retail", "grocery", "supermarket",
    "nutrition", "health food", "organic", "dairy", "bakery",
    "confectionery", "tobacco", "alcohol", "beer", "wine", "spirits",
]

DEAL_KEYWORDS = [
    "acquisition", "merger", "acquire", "buyout", "investment",
    "stake", "deal", "takeover", "purchase", "funding", "raise",
    "private equity", "venture capital", "ipo", "joint venture",
    "strategic partnership", "divest", "spin-off",
]


def _build_queries(market: str = "global") -> List[str]:
    now = datetime.now()
    year = now.year
    month = now.strftime("%B")
    prev_month = datetime(now.year, now.month - 1 if now.month > 1 else 12, 1).strftime("%B")
    year_prev = year - 1

    geo = MARKETS.get(market, MARKETS["global"])["geo_terms"]
    geo_str = geo[0] if geo else ""
    geo_suffix = f" {geo_str}" if geo_str else ""
    geo_alt = f" {geo[1]}" if len(geo) > 1 else geo_suffix

    base = [
        f"FMCG company acquired{geo_suffix} {year} deal announced billion million",
        f"food brand acquisition announced{geo_suffix} {month} {year}",
        f"beverage company merger agreement signed{geo_suffix} {year}",
        f"consumer goods buyout private equity{geo_suffix} {year} completed",
        f"personal care beauty brand acquired{geo_suffix} {year}",
        f"household products company takeover bid{geo_suffix} {year}",
        f"CPG brand acquisition closes{geo_suffix} {year} investment",
        f"food drink company merger announced{geo_suffix} {prev_month} {month} {year}",
        f"FMCG startup acquisition funding round{geo_suffix} {year}",
        f"consumer goods M&A deal{geo_suffix} {year_prev} {year} signed closed",
    ]

    if geo_str:
        base += [
            f"{geo_str} FMCG M&A news {month} {year}",
            f"{geo_str} food beverage acquisition deal {year}",
            f"{geo_alt} consumer brand merger investment {year}",
        ]
    else:
        base += [
            f"Unilever Nestle PepsiCo Mondelez acquisition deal {year}",
            f"global FMCG deal activity {month} {year}",
        ]

    return base


def search_news(market: str = "global") -> List[dict]:
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    queries = _build_queries(market)
    results = []
    seen_urls = set()
    for query in queries:
        try:
            response = tavily.search(
                query=query,
                search_depth="advanced",
                max_results=10,
                include_raw_content=True,
                days=30,
            )
            for r in response.get("results", []):
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    results.append(r)
        except Exception:
            continue
    return results


def make_article_id(title: str, url: str) -> str:
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]


def extract_domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else ""


def score_relevance(title: str, content: str) -> float:
    text = f"{title} {content}".lower()
    fmcg_hits = sum(1 for kw in FMCG_KEYWORDS if kw in text)
    deal_hits = sum(1 for kw in DEAL_KEYWORDS if kw in text)
    score = min(1.0, (fmcg_hits * 0.06) + (deal_hits * 0.08))
    return round(score, 3)


def score_credibility(url: str, market: str = "global") -> float:
    domain = extract_domain(url)
    if any(s in domain for s in SOCIAL_DOMAINS):
        return 0.20
    domain_map = MARKET_DOMAINS.get(market, MARKET_DOMAINS["global"])
    for known, score in domain_map.items():
        if known in domain:
            return score
    global_map = MARKET_DOMAINS["global"]
    for known, score in global_map.items():
        if known in domain:
            return score
    return 0.46


def deduplicate(articles: List[Article]) -> List[Article]:
    seen_titles = {}
    unique = []
    for art in articles:
        normalized = re.sub(r"[^a-z0-9 ]", "", art["title"].lower()).strip()
        words = set(normalized.split())
        is_dup = False
        for seen_words in seen_titles.values():
            overlap = len(words & seen_words) / max(len(words | seen_words), 1)
            if overlap > 0.7:
                is_dup = True
                break
        if not is_dup:
            seen_titles[normalized] = words
            unique.append(art)
    return unique


def parse_raw_results(raw: List[dict]) -> List[Article]:
    articles = []
    for r in raw:
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("raw_content") or r.get("content", "")
        articles.append(Article(
            id=make_article_id(title, url),
            title=title,
            url=url,
            source=extract_domain(url),
            published_date=r.get("published_date", ""),
            content=content[:2000],
            relevance_score=0.0,
            credibility_score=0.0,
            deal_type="",
            companies=[],
            deal_value="",
            geography="",
        ))
    return articles
