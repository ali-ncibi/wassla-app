import hmac
import time
from typing import cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from openinference.instrumentation import using_tags

from ..graph.nodes import Deps
from ..graph.pipeline import build_pipeline_graph
from ..graph.state import PipelineState
from ..schemas import ArticleSummary, IngestRequest, IngestResponse

router = APIRouter()


def get_deps(request: Request) -> Deps:
    return cast(Deps, request.app.state.deps)


def check_ingest_token(deps: Deps, token: str | None) -> None:
    if not deps.settings.ingest_token:
        raise HTTPException(status_code=503, detail="Ingest disabled: INGEST_TOKEN is not set")
    if not token or not hmac.compare_digest(token, deps.settings.ingest_token):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ingest-Token")


@router.post("/ingest/run", response_model=IngestResponse)
async def run_ingest(
    payload: IngestRequest | None = None,
    deps: Deps = Depends(get_deps),
    x_ingest_token: str | None = Header(default=None),
) -> IngestResponse:
    check_ingest_token(deps, x_ingest_token)
    started = time.perf_counter()
    graph = build_pipeline_graph(deps)
    initial: PipelineState = (
        PipelineState(max_items=payload.max_items) if payload and payload.max_items else PipelineState()
    )
    with using_tags(["ingest"]):
        final = cast(
            "PipelineState",
            await graph.ainvoke(initial, config={"tags": ["ingest"], "run_name": "ingest"}),
        )
    duration_ms = int((time.perf_counter() - started) * 1000)
    articles = [ArticleSummary(**r) for r in final.get("results", []) if "id" in r]
    errors = final.get("errors", [])
    return IngestResponse(
        fetched=final.get("fetched_count", 0),
        duplicates_skipped=final.get("duplicates", 0),
        processed=len(articles),
        failed=len(errors),
        duration_ms=duration_ms,
        articles=articles,
        errors=errors[:20],
    )
