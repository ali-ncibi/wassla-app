import sys
import types

from app.observability import setup_tracing

from .conftest import make_settings


def test_setup_tracing_registers_and_instruments(monkeypatch) -> None:
    calls: dict[str, dict] = {}

    def fake_module(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        mod.__path__ = []  # type: ignore[attr-defined]
        return mod

    phoenix = fake_module("phoenix")
    phoenix_otel = fake_module("phoenix.otel")

    def register(**kwargs: object) -> str:
        calls["register"] = kwargs  # type: ignore[assignment]
        return "tracer-provider"

    phoenix_otel.register = register  # type: ignore[attr-defined]
    phoenix.otel = phoenix_otel  # type: ignore[attr-defined]

    openinference = fake_module("openinference")
    oi_instrumentation = fake_module("openinference.instrumentation")
    oi_langchain = fake_module("openinference.instrumentation.langchain")

    class LangChainInstrumentor:
        def instrument(self, **kwargs: object) -> None:
            calls["instrument"] = kwargs  # type: ignore[assignment]

    oi_langchain.LangChainInstrumentor = LangChainInstrumentor  # type: ignore[attr-defined]
    openinference.instrumentation = oi_instrumentation  # type: ignore[attr-defined]
    oi_instrumentation.langchain = oi_langchain  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "phoenix", phoenix)
    monkeypatch.setitem(sys.modules, "phoenix.otel", phoenix_otel)
    monkeypatch.setitem(sys.modules, "openinference", openinference)
    monkeypatch.setitem(sys.modules, "openinference.instrumentation", oi_instrumentation)
    monkeypatch.setitem(sys.modules, "openinference.instrumentation.langchain", oi_langchain)

    settings = make_settings(phoenix_collector_endpoint="http://phoenix:6006/v1/traces", phoenix_project_name="proj")
    setup_tracing(settings)

    assert calls["register"]["endpoint"] == "http://phoenix:6006/v1/traces"
    assert calls["register"]["project_name"] == "proj"
    assert calls["instrument"]["tracer_provider"] == "tracer-provider"


def test_phoenix_defaults(monkeypatch) -> None:
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)
    s = make_settings()
    assert s.phoenix_collector_endpoint == "http://phoenix:6006/v1/traces"
    assert s.phoenix_project_name == "wassla-pipeline"
