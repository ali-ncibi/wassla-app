from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings


def setup_tracing(settings: Settings) -> None:
    """Send OpenInference/OTLP spans of the LangGraph workflow to the Phoenix collector.

    Always on: the pipeline runs in docker compose next to the `phoenix` service, which
    receives spans at ``phoenix_collector_endpoint``. Must run before langchain/langgraph
    modules are imported so the instrumentor can patch them (see app/main.py).
    """
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from phoenix.otel import register

    tracer_provider = register(
        endpoint=settings.phoenix_collector_endpoint,
        project_name=settings.phoenix_project_name,
        verbose=False,
    )
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider, skip_dep_check=True)
