from fastapi import APIRouter, Depends, HTTPException, Query

from .. import repo
from ..graph.nodes import Deps
from ..schemas import ArticleCard, ArticleDetail, ArticlesResponse, CategoryCount
from .ingest import get_deps

router = APIRouter()


@router.get("/articles", response_model=ArticlesResponse)
async def list_articles(
    lang: str = Query(default="en"),
    category: str | None = Query(default=None),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: Deps = Depends(get_deps),
) -> ArticlesResponse:
    if lang not in deps.settings.language_list:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")
    total, rows = await repo.list_articles(deps.pool, lang, category, limit, offset)
    return ArticlesResponse(total=total, items=[ArticleCard(**r) for r in rows])


@router.get("/articles/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: int,
    lang: str = Query(default="en"),
    deps: Deps = Depends(get_deps),
) -> ArticleDetail:
    if lang not in deps.settings.language_list:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")
    row = await repo.get_article(deps.pool, article_id, lang)
    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleDetail(**row)


@router.get("/categories", response_model=list[CategoryCount])
async def list_categories(deps: Deps = Depends(get_deps)) -> list[CategoryCount]:
    return [CategoryCount(**r) for r in await repo.category_counts(deps.pool)]
