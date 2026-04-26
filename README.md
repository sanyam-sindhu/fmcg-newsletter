# FMCG M&A Newsletter Generator

A tool that automatically researches, filters, and writes a Bloomberg-style M&A briefing for the FMCG sector. Powered by a LangGraph agent pipeline, OpenAI GPT-4o, and Tavily Search.

Live at: https://fmcg-newsletter.vercel.app
Backend: https://fmcg-newsletter.onrender.com

---

## API

Base URL: https://fmcg-newsletter.onrender.com

**GET /api/markets**
Returns the list of supported markets.

**GET /api/history**
Returns all runs from the current session.

**GET /health**
Health check. Returns ok if the server is up.

**POST /api/run**
Starts a new pipeline run. Returns a run_id immediately while the pipeline runs in the background.

Request body:
```json
{
  "market": "india",
  "as_of_date": "2026-04-26"
}
```

**GET /api/status/{run_id}**
Poll this to check progress. Returns the current status and article counts at each pipeline stage.

**GET /api/result/{run_id}**
Returns the completed newsletter, structured sections, and all articles with metadata. Only available once status is "generated".

**GET /api/result/{run_id}/csv**
Downloads a CSV of all final articles.

**GET /api/result/{run_id}/excel**
Downloads an Excel file with three sheets covering the newsletter sections, articles table, and pipeline stats.

**GET /api/result/{run_id}/word**
Downloads the newsletter as a Word document.

**GET /api/result/{run_id}/pptx**
Downloads a PowerPoint with 7 slides covering the full briefing.

---

## What it does

You pick a market and a date, hit Generate, and within a few minutes you get a formatted newsletter with executive summary, top deals, sector and geographic breakdown, and market outlook. All source articles are shown with their relevance and credibility scores. You can export everything to CSV, Excel, Word, or PowerPoint.

The pipeline runs entirely automatically. It searches the web, removes duplicate stories, filters out irrelevant or low-credibility sources, extracts deal metadata using GPT-4o, then writes the newsletter.

---

## How the pipeline works

There are six steps, each running as a LangGraph node.

**Search** runs 10 to 13 Tavily queries tailored to the selected market and current date. Queries are dynamic so you always get fresh results rather than cached ones.

**Deduplication** normalises titles and computes Jaccard similarity between word sets. Anything with more than 70% overlap is dropped as a near-duplicate.

**Relevance filter** scores each article by keyword density across FMCG terms like food, beverage, and personal care, combined with deal terms like acquisition, merger, and stake. Articles below a score of 0.15 are dropped.

**Credibility check** looks up each article's domain against a trust map of over 30 known sources with market-specific overrides. For example The Grocer is weighted higher for UK runs, VCCircle for India. Social media is always blocked.

**Enrichment** sends each surviving article to GPT-4o which extracts deal type, companies involved, deal value, and geography in structured JSON.

**Newsletter generation** uses GPT-4o to write the final briefing in Bloomberg style. A second pass then parses it into structured sections used by the export formats.

State is persisted in PostgreSQL via LangGraph's PostgresSaver so every run is checkpointed and reloadable from the history panel even after a page refresh.

---

## Markets supported

**global** covers general FMCG M&A worldwide.

**india** uses sources like Economic Times, LiveMint, VCCircle, and Business Standard with India-specific search queries.

**usa** uses sources like WSJ, Food Dive, Grocery Dive, and Supermarket News.

**uk** uses sources like FT, The Grocer, Grocery Gazette, and Food Manufacture.

**europe** uses sources like FT, Food Navigator, and Food Bev.

**asia_pacific** uses sources like DealStreetAsia, Nikkei, SCMP, and Straits Times.

Each market has its own set of search queries and its own domain credibility map. Queries include the current month and year automatically so results stay fresh on every run.

---

## Tech stack

Agent pipeline is built on LangGraph using StateGraph with PostgresSaver for checkpointing.

LLM is OpenAI GPT-4o accessed via langchain-openai.

Web search is Tavily Search API.

Backend is FastAPI with ThreadPoolExecutor handling concurrent pipeline runs.

Database is PostgreSQL hosted on Neon.

Frontend is React with Vite and Tailwind CSS.

Exports are generated using python-docx, openpyxl, and python-pptx.

Hosting is Render for the backend and Vercel for the frontend.

---

## Project structure

```
backend/
  main.py         FastAPI app and all API endpoints
  agent.py        LangGraph nodes and graph definition
  state.py        TypedDict definitions for pipeline state
  tools.py        Search, dedup, relevance and credibility scoring
  exports.py      Word and Excel generation
  ppt_export.py   PowerPoint generation

frontend/
  src/
    App.jsx
    components/
      NewsletterView.jsx
      ArticleTable.jsx
      PipelineStats.jsx
      MarketSelector.jsx
      RunHistory.jsx
      StatusBadge.jsx
```

---

## Local setup

You need Python 3.12, Node 18+, and a PostgreSQL database.

Clone the repo and set up the backend first:

```bash
cd backend
pip install -r requirements.txt
```

Create a .env file inside the backend folder:

```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
DATABASE_URL=postgresql://...
```

Start the backend:

```bash
python main.py
```

Then set up the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

---

## Concurrency

Multiple users can run the pipeline at the same time. Each run gets its own thread from a pool of 20 workers so the FastAPI event loop stays unblocked. The PostgreSQL connection pool handles simultaneous checkpoint reads and writes. Each run is isolated by its run_id which maps to the LangGraph thread_id.
