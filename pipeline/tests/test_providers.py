import json
from typing import Any

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.providers import build_chat_model, build_chat_models, build_embeddings
from app.providers.chat import OpenAICompatibleChatModel, StubChatModel, to_api_messages
from app.providers.embeddings import OpenAICompatibleEmbeddings, StubEmbeddings

from .conftest import make_settings


def test_to_api_messages_roles_and_non_string_content() -> None:
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="hi"),
        AIMessage(content="yo"),
        HumanMessage(content=[{"type": "text", "text": "x"}]),
    ]
    out = to_api_messages(msgs)
    assert out[0] == {"role": "system", "content": "sys"}
    assert out[1] == {"role": "user", "content": "hi"}
    assert out[2] == {"role": "assistant", "content": "yo"}
    assert json.loads(out[3]["content"]) == [{"type": "text", "text": "x"}]


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class _FakeClient:
    instances: list["_FakeClient"] = []

    def __init__(self, timeout: float | None = None) -> None:
        self.timeout = timeout
        self.posts: list[tuple[str, dict[str, Any], dict[str, str]]] = []
        self.response: dict[str, Any] = {"choices": [{"message": {"content": "ok"}}]}
        _FakeClient.instances.append(self)

    def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> _FakeResp:
        self.posts.append((url, json, headers))
        return _FakeResp(self.response)

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False


def test_openai_compatible_chat_model_posts_payload(monkeypatch) -> None:
    import app.providers.chat as chat_mod

    monkeypatch.setattr(chat_mod.httpx, "Client", _FakeClient)
    _FakeClient.instances.clear()
    model = OpenAICompatibleChatModel(
        base_url="http://api.test/v1/", api_key="k", model="m", temperature=0.5, timeout=12.0, json_mode=True
    )
    assert model._llm_type == "openai-compatible-chat"
    assert StubChatModel()._llm_type == "stub-chat"
    result = model._generate([HumanMessage(content="hi")], None, None)
    assert result.generations[0].message.content == "ok"
    client = _FakeClient.instances[0]
    url, payload, headers = client.posts[0]
    assert url == "http://api.test/v1/chat/completions"
    assert payload["model"] == "m"
    assert payload["temperature"] == 0.5
    assert payload["messages"] == [{"role": "user", "content": "hi"}]
    assert payload["response_format"] == {"type": "json_object"}
    assert headers == {"Authorization": "Bearer k", "Content-Type": "application/json"}
    assert client.timeout == 12.0


def test_openai_compatible_chat_model_without_json_mode(monkeypatch) -> None:
    import app.providers.chat as chat_mod

    monkeypatch.setattr(chat_mod.httpx, "Client", _FakeClient)
    _FakeClient.instances.clear()
    model = OpenAICompatibleChatModel(base_url="http://api.test", api_key="k", model="m", json_mode=False)
    model._generate([HumanMessage(content="hi")], None, None)
    _, payload, _ = _FakeClient.instances[0].posts[0]
    assert "response_format" not in payload


def test_stub_chat_model_replies_per_task() -> None:
    model = StubChatModel()
    translate = model._generate(
        [
            SystemMessage(content="x"),
            HumanMessage(content="TRANSLATION TASK\nTarget language: ar\n\nTITLE:\nHello\n\nBODY:\nSome body text"),
        ],
        None,
        None,
    )
    data = json.loads(str(translate.generations[0].message.content))
    assert data["title"] == "[ar] Hello"
    assert data["body"].startswith("[ar] Some body text")

    cat = model._generate(
        [
            HumanMessage(
                content="CATEGORIZATION TASK\nCategories: []\n\nTITLE:\nVote\n\nBODY:\nThe parliament election vote senate"
            )
        ],
        None,
        None,
    )
    assert json.loads(str(cat.generations[0].message.content))["category"] == "politics"

    summ = model._generate(
        [HumanMessage(content="SUMMARIZATION TASK\nLanguage: en\n\nTITLE:\nt\n\nBODY:\n" + "word " * 100)],
        None,
        None,
    )
    assert len(str(summ.generations[0].message.content).split()) == 60

    ev = model._generate([HumanMessage(content="EVALUATION TASK\n{}")], None, None)
    assert json.loads(str(ev.generations[0].message.content)) == {"score": 8.0, "verdict": "pass", "issues": []}

    other = model._generate([HumanMessage(content="something else")], None, None)
    assert other.generations[0].message.content == "stub response"


def test_stub_embeddings_shape_norm_and_determinism() -> None:
    emb = StubEmbeddings(dim=8)
    v1 = emb.embed_query("hello world hello")
    v2 = emb.embed_query("hello world hello")
    v3 = emb.embed_query("completely different text")
    assert v1 == v2
    assert v1 != v3
    assert len(v1) == 8
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-9
    zero = emb.embed_query("!!!")
    assert all(x == 0.0 for x in zero)
    assert emb.embed_documents(["a", "b"]) == [emb.embed_query("a"), emb.embed_query("b")]


def test_openai_compatible_embeddings_reorders_by_index(monkeypatch) -> None:
    import app.providers.embeddings as emb_mod

    class _EmbClient(_FakeClient):
        pass

    monkeypatch.setattr(emb_mod.httpx, "Client", _EmbClient)
    _EmbClient.instances.clear()

    emb = OpenAICompatibleEmbeddings(base_url="http://api.test/v1", api_key="k", model="emb-model", timeout=5.0)

    def post(self, url, json, headers):  # type: ignore[no-untyped-def]
        self.posts.append((url, json, headers))
        return _FakeResp({"data": [{"index": 1, "embedding": [0.2]}, {"index": 0, "embedding": [0.1]}]})

    _EmbClient.post = post  # type: ignore[method-assign]
    vecs = emb.embed_documents(["b", "a"])
    assert vecs == [[0.1], [0.2]]
    url, payload, headers = _EmbClient.instances[0].posts[0]
    assert url == "http://api.test/v1/embeddings"
    assert payload == {"model": "emb-model", "input": ["b", "a"]}
    assert headers["Authorization"] == "Bearer k"
    assert emb.embed_query("q") == [0.1]


def test_build_chat_model_stub() -> None:
    s = make_settings(llm_provider="stub")
    model = build_chat_model(s, "translate")
    assert isinstance(model, StubChatModel)
    assert isinstance(model, BaseChatModel)


def test_build_chat_model_mistral_requires_key() -> None:
    s = make_settings(llm_provider="mistral", mistral_api_key="")
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        build_chat_model(s, "translate")


def test_build_chat_model_mistral_per_task_models_and_json_mode() -> None:
    s = make_settings(llm_provider="mistral", mistral_api_key="k")
    expected = {
        "translate": ("mistral-small-latest", True),
        "categorize": ("mistral-small-latest", True),
        "summarize": ("mistral-small-latest", False),
        "evaluate": ("mistral-medium-latest", True),
        "unknown-task": ("mistral-small-latest", False),
    }
    for task, (model_name, json_mode) in expected.items():
        m = build_chat_model(s, task)
        assert isinstance(m, OpenAICompatibleChatModel)
        assert m.model == model_name
        assert m.json_mode == json_mode
        assert m.base_url == "https://api.mistral.ai/v1"


def test_build_chat_model_openai() -> None:
    s = make_settings(llm_provider="openai", openai_api_key="")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_chat_model(s, "translate")
    s2 = make_settings(llm_provider="openai", openai_api_key="k")
    m = build_chat_model(s2, "summarize")
    assert isinstance(m, OpenAICompatibleChatModel)
    assert m.model == "gpt-4o-mini"


def test_build_chat_model_unknown_provider() -> None:
    s = make_settings(llm_provider="nope")
    with pytest.raises(ValueError, match="Unknown llm_provider"):
        build_chat_model(s, "translate")


def test_build_embeddings_stub() -> None:
    s = make_settings(embedding_provider="stub", embedding_dim=64)
    emb = build_embeddings(s)
    assert isinstance(emb, StubEmbeddings)
    assert isinstance(emb, Embeddings)
    assert emb.dim == 64


def test_build_embeddings_mistral_and_openai() -> None:
    s = make_settings(embedding_provider="mistral", mistral_api_key="")
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        build_embeddings(s)
    s2 = make_settings(embedding_provider="mistral", mistral_api_key="k")
    e = build_embeddings(s2)
    assert isinstance(e, OpenAICompatibleEmbeddings)
    assert e.model == "mistral-embed"
    s3 = make_settings(embedding_provider="openai", openai_api_key="")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_embeddings(s3)
    s3b = make_settings(embedding_provider="openai", openai_api_key="k")
    e3 = build_embeddings(s3b)
    assert isinstance(e3, OpenAICompatibleEmbeddings)
    assert e3.model == "text-embedding-3-small"
    s4 = make_settings(embedding_provider="nope")
    with pytest.raises(ValueError, match="Unknown embedding_provider"):
        build_embeddings(s4)


def test_build_chat_models_keys() -> None:
    models = build_chat_models(make_settings(llm_provider="stub"))
    assert set(models) == {"translate", "categorize", "summarize", "evaluate"}
    assert all(isinstance(m, StubChatModel) for m in models.values())
