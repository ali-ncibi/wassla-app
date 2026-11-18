from fastapi import APIRouter, Depends
from langchain_core.language_models.chat_models import BaseChatModel

from .. import repo
from ..graph.nodes import Deps
from ..schemas import ConfigView, HealthResponse, RagConfig, StatsResponse
from .ingest import get_deps

router = APIRouter()


def model_name(model: BaseChatModel) -> str:
    return str(getattr(model, "model", "unknown"))


@router.get("/health", response_model=HealthResponse)
async def health(deps: Deps = Depends(get_deps)) -> HealthResponse:
    try:
        async with deps.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "ok"
    except Exception:
        db_status = "error"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        llm_provider=deps.settings.llm_provider,
        llm_models={task: model_name(m) for task, m in deps.chat.items()},
        embedding_provider=deps.settings.embedding_provider,
        embedding_dim=deps.settings.embedding_dim,
    )


@router.get("/config", response_model=ConfigView)
async def get_config(deps: Deps = Depends(get_deps)) -> ConfigView:
    s = deps.settings
    return ConfigView(
        llm_provider=s.llm_provider,
        embedding_provider=s.embedding_provider,
        languages=s.language_list,
        categories=s.category_list,
        models={task: model_name(m) for task, m in deps.chat.items()},
        eval_min_score=s.eval_min_score,
        ingest_max_items=s.ingest_max_items,
        rag=RagConfig(top_k=s.rag_top_k, min_score=s.rag_min_score, answer_enabled=s.rag_answer_enabled),
    )


@router.get("/stats", response_model=StatsResponse)
async def stats(deps: Deps = Depends(get_deps)) -> StatsResponse:
    data = await repo.stats(deps.pool)
    return StatsResponse(**data, per_day_target=200)
