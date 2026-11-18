from app.config import Settings, get_settings

from .conftest import make_settings


def test_defaults() -> None:
    s = make_settings()
    assert s.app_name == "wassla-pipeline"
    assert s.llm_provider == "mistral"
    assert s.embedding_provider == "mistral"
    assert s.llm_temperature == 0.2
    assert s.llm_max_concurrency == 4
    assert s.embedding_dim == 1024
    assert s.eval_min_score == 6.0
    assert s.ingest_max_items == 50
    assert s.rag_top_k == 5
    assert s.rag_min_score == 0.35
    assert s.rag_answer_enabled is True
    assert s.ingest_token == ""


def test_list_properties_strip_and_skip_empty() -> None:
    s = make_settings(languages=" en , fr ,, ar ", categories="world, politics", cors_origins=" http://a ,http://b")
    assert s.language_list == ["en", "fr", "ar"]
    assert s.category_list == ["world", "politics"]
    assert s.cors_origin_list == ["http://a", "http://b"]


def test_default_lists() -> None:
    s = make_settings()
    assert s.language_list == ["en", "fr", "ar"]
    assert s.category_list[0] == "world"
    assert len(s.category_list) == 9
    assert s.cors_origin_list == ["http://localhost:3000"]


def test_get_settings_reads_env_and_caches(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/wassla")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.database_url == "postgresql://u:p@db:5432/wassla"
        assert s.llm_provider == "stub"
        assert get_settings() is s
    finally:
        get_settings.cache_clear()


def test_settings_requires_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import pydantic

    try:
        Settings(_env_file=None)  # type: ignore[call-arg]
    except pydantic.ValidationError:
        pass
    else:
        raise AssertionError("Settings without database_url should fail validation")
