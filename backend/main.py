import os
import uuid
import asyncio
import traceback
import sys
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import date as _date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from agent import build_graph
from state import NewsletterState
from exports import generate_word, generate_excel
from ppt_export import generate_pptx
from tools import MARKETS

DB_URL = os.getenv("DATABASE_URL")
graph = None
pool = None
executor = ThreadPoolExecutor(max_workers=20)
active_runs: dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, pool
    pool = ConnectionPool(
        DB_URL,
        max_size=20,
        max_idle=300,
        reconnect_timeout=30,
        kwargs={"keepalives": 1, "keepalives_idle": 60, "keepalives_interval": 10, "keepalives_count": 5},
    )
    with pool.connection() as conn:
        conn.autocommit = True
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
    graph = build_graph(PostgresSaver(pool))
    yield
    pool.close()
    executor.shutdown(wait=False)


app = FastAPI(title="FMCG Newsletter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    run_id: str | None = None
    market: str = "global"
    as_of_date: str | None = None


@app.get("/api/markets")
async def list_markets():
    return {"markets": [{"key": k, "label": v["label"]} for k, v in MARKETS.items()]}


@app.post("/api/run")
async def start_run(req: RunRequest):
    run_id = req.run_id or str(uuid.uuid4())
    market = req.market if req.market in MARKETS else "global"
    as_of_date = req.as_of_date or str(_date.today())
    active_runs[run_id] = "running"

    config = {"configurable": {"thread_id": run_id}}
    initial_state = NewsletterState(
        messages=[],
        market=market,
        as_of_date=as_of_date,
        raw_articles=[],
        deduplicated_articles=[],
        filtered_articles=[],
        credibility_checked_articles=[],
        newsletter_draft="",
        newsletter_sections={},
        csv_data="",
        run_id=run_id,
        status="started",
        error=None,
    )

    def run_pipeline():
        try:
            graph.invoke(initial_state, config)
            active_runs[run_id] = "done"
        except Exception as e:
            print(f"PIPELINE ERROR:\n{traceback.format_exc()}", file=sys.stderr, flush=True)
            active_runs[run_id] = f"error:{str(e)}"

    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_pipeline)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/status/{run_id}")
async def get_status(run_id: str):
    config = {"configurable": {"thread_id": run_id}}
    loop = asyncio.get_event_loop()
    try:
        snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
        if snapshot and snapshot.values:
            state = snapshot.values
            return {
                "run_id": run_id,
                "status": state.get("status", "unknown"),
                "market": state.get("market", "global"),
                "article_counts": {
                    "raw": len(state.get("raw_articles", [])),
                    "deduplicated": len(state.get("deduplicated_articles", [])),
                    "filtered": len(state.get("filtered_articles", [])),
                    "final": len(state.get("credibility_checked_articles", [])),
                },
            }
    except Exception:
        pass
    return {"run_id": run_id, "status": active_runs.get(run_id, "not_found")}


@app.get("/api/result/{run_id}")
async def get_result(run_id: str):
    config = {"configurable": {"thread_id": run_id}}
    loop = asyncio.get_event_loop()
    snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found or not complete")

    state = snapshot.values
    if state.get("status") != "generated":
        raise HTTPException(status_code=202, detail=f"Pipeline status: {state.get('status')}")

    articles = state.get("credibility_checked_articles", [])
    return {
        "run_id": run_id,
        "market": state.get("market", "global"),
        "as_of_date": state.get("as_of_date", ""),
        "newsletter_draft": state.get("newsletter_draft", ""),
        "newsletter_sections": state.get("newsletter_sections", {}),
        "articles": articles,
        "article_count": len(articles),
        "pipeline_stats": {
            "raw": len(state.get("raw_articles", [])),
            "after_dedup": len(state.get("deduplicated_articles", [])),
            "after_filter": len(state.get("filtered_articles", [])),
            "after_credibility": len(articles),
        },
    }


@app.get("/api/result/{run_id}/csv")
async def get_csv(run_id: str):
    loop = asyncio.get_event_loop()
    config = {"configurable": {"thread_id": run_id}}
    snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found")
    csv_data = snapshot.values.get("csv_data", "")
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=fmcg_deals_{run_id[:8]}.csv"},
    )


@app.get("/api/result/{run_id}/word")
async def get_word(run_id: str):
    loop = asyncio.get_event_loop()
    config = {"configurable": {"thread_id": run_id}}
    snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found")
    state = snapshot.values
    doc_bytes = generate_word(
        state.get("newsletter_draft", ""),
        state.get("credibility_checked_articles", []),
        run_id,
    )
    return StreamingResponse(
        iter([doc_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=fmcg_newsletter_{run_id[:8]}.docx"},
    )


@app.get("/api/result/{run_id}/excel")
async def get_excel(run_id: str):
    loop = asyncio.get_event_loop()
    config = {"configurable": {"thread_id": run_id}}
    snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found")
    state = snapshot.values
    xl_bytes = generate_excel(
        state.get("credibility_checked_articles", []),
        state.get("newsletter_sections", {}),
        run_id,
    )
    return StreamingResponse(
        iter([xl_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=fmcg_newsletter_{run_id[:8]}.xlsx"},
    )


@app.get("/api/result/{run_id}/pptx")
async def get_pptx(run_id: str):
    loop = asyncio.get_event_loop()
    config = {"configurable": {"thread_id": run_id}}
    snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found")
    state = snapshot.values
    pptx_bytes = generate_pptx(
        state.get("newsletter_draft", ""),
        state.get("newsletter_sections", {}),
        state.get("credibility_checked_articles", []),
        {
            "raw": len(state.get("raw_articles", [])),
            "after_dedup": len(state.get("deduplicated_articles", [])),
            "after_filter": len(state.get("filtered_articles", [])),
            "after_credibility": len(state.get("credibility_checked_articles", [])),
        },
        run_id,
    )
    return StreamingResponse(
        iter([pptx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=fmcg_newsletter_{run_id[:8]}.pptx"},
    )


@app.get("/api/history")
async def list_runs():
    loop = asyncio.get_event_loop()
    runs = []
    for run_id, hist_status in list(active_runs.items()):
        config = {"configurable": {"thread_id": run_id}}
        entry = {"run_id": run_id, "status": hist_status, "article_count": 0, "market": "global", "timestamp": ""}
        try:
            snapshot = await loop.run_in_executor(executor, lambda: graph.get_state(config))
            if snapshot and snapshot.values:
                state = snapshot.values
                entry["status"] = state.get("status", hist_status)
                entry["market"] = state.get("market", "global")
                entry["article_count"] = len(state.get("credibility_checked_articles", []))
        except Exception:
            pass
        runs.append(entry)
    runs.reverse()
    return {"runs": runs}


@app.get("/health")
async def health():
    return {"status": "ok", "active_runs": len(active_runs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
