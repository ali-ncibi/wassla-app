from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from .nodes import (
    Deps,
    make_categorize_node,
    make_embed_node,
    make_evaluate_node,
    make_fetch_node,
    make_persist_node,
    make_process_article_node,
    make_summarize_node,
    make_translate_node,
)
from .state import ArticleState, PipelineState, require


def build_article_graph(deps: Deps, *, persist: bool = True) -> CompiledStateGraph[ArticleState]:
    graph = StateGraph(ArticleState)
    graph.add_node("translate", make_translate_node(deps))
    graph.add_node("categorize", make_categorize_node(deps))
    graph.add_node("summarize", make_summarize_node(deps))
    graph.add_node("evaluate", make_evaluate_node(deps))
    graph.add_node("embed", make_embed_node(deps))
    graph.add_edge(START, "translate")
    graph.add_edge("translate", "categorize")
    graph.add_edge("categorize", "summarize")
    graph.add_edge("summarize", "evaluate")
    graph.add_edge("evaluate", "embed")
    if persist:
        graph.add_node("persist", make_persist_node(deps))
        graph.add_edge("embed", "persist")
        graph.add_edge("persist", END)
    else:
        graph.add_edge("embed", END)
    return graph.compile()


def route_to_articles(state: PipelineState) -> list[Send]:
    return [Send("process_article", {"item": item}) for item in require(state, "items")]


def build_pipeline_graph(deps: Deps) -> CompiledStateGraph[PipelineState]:
    article_graph = build_article_graph(deps)
    graph = StateGraph(PipelineState)
    graph.add_node("fetch", make_fetch_node(deps))
    graph.add_node("process_article", make_process_article_node(article_graph, deps))
    graph.add_edge(START, "fetch")
    graph.add_conditional_edges("fetch", route_to_articles, ["process_article"])
    graph.add_edge("process_article", END)
    return graph.compile()
