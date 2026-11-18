from fastapi import APIRouter, Depends, HTTPException, Query

from ..graph.nodes import Deps
from ..rag import rag_search
from ..schemas import RagConfig, SearchResponse
from .ingest import get_deps

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=2, max_length=500),
    lang: str = Query(default="en"),
    top_k: int | None = Query(default=None, ge=1, le=50),
    deps: Deps = Depends(get_deps),
) -> SearchResponse:
    if lang not in deps.settings.language_list:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")
    s = deps.settings
    rag = RagConfig(top_k=s.rag_top_k, min_score=s.rag_min_score, answer_enabled=s.rag_answer_enabled)
    try:
        return await rag_search(deps, q.strip(), lang, rag, top_k_override=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
