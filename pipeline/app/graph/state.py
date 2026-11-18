from operator import add
from typing import Annotated, Any, Literal, TypedDict, overload

from ..feeds import FeedItem
from ..schemas import TranslationDraft


class ArticleState(TypedDict, total=False):
    item: FeedItem
    translations: dict[str, TranslationDraft]
    category: str
    summaries: dict[str, str]
    evaluation: dict[str, Any]
    embeddings: dict[str, list[float]]
    article_id: int


class PipelineState(TypedDict, total=False):
    max_items: int
    items: list[FeedItem]
    fetched_count: int
    duplicates: int
    results: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[str], add]


@overload
def require(state: ArticleState, key: Literal["item"]) -> FeedItem: ...
@overload
def require(state: ArticleState, key: Literal["translations"]) -> dict[str, TranslationDraft]: ...
@overload
def require(state: ArticleState, key: Literal["category"]) -> str: ...
@overload
def require(state: ArticleState, key: Literal["summaries"]) -> dict[str, str]: ...
@overload
def require(state: ArticleState, key: Literal["evaluation"]) -> dict[str, Any]: ...
@overload
def require(state: ArticleState, key: Literal["embeddings"]) -> dict[str, list[float]]: ...
@overload
def require(state: ArticleState, key: Literal["article_id"]) -> int: ...
@overload
def require(state: PipelineState, key: Literal["items"]) -> list[FeedItem]: ...
def require(state: ArticleState | PipelineState, key: str) -> Any:
    if key not in state:
        msg = f"missing required graph state key: {key!r}"
        raise KeyError(msg)
    return state.get(key)
