from . import repo
from .graph.nodes import Deps, call_llm
from .graph.prompts import answer_messages
from .schemas import RagConfig, SearchHit, SearchResponse


async def rag_search(
    deps: Deps,
    query: str,
    lang: str,
    rag: RagConfig,
    top_k_override: int | None = None,
) -> SearchResponse:
    if lang not in deps.settings.language_list:
        msg = f"Unsupported language: {lang}"
        raise ValueError(msg)
    top_k = top_k_override or rag.top_k
    async with deps.semaphore:
        query_vec = await deps.embedder.aembed_query(query)
    rows = await repo.search_translations(deps.pool, query_vec, lang, top_k)
    hits = [
        SearchHit(**{**r, "score": round(float(r["score"]), 4)}) for r in rows if float(r["score"]) >= rag.min_score
    ]
    answer: str | None = None
    if rag.answer_enabled and hits:
        snippets = [f"{h.title}\n{h.summary or ''}\n{h.url}" for h in hits]
        answer = (await call_llm(deps, "summarize", answer_messages(lang, query, snippets))).strip()
    return SearchResponse(query=query, lang=lang, answer=answer, hits=hits)
