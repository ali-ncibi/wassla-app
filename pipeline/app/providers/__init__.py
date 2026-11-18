from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from ..config import Settings
from .chat import OpenAICompatibleChatModel, StubChatModel
from .embeddings import OpenAICompatibleEmbeddings, StubEmbeddings

TaskName = str


def build_chat_model(settings: Settings, task: TaskName) -> BaseChatModel:
    if settings.llm_provider == "stub":
        return StubChatModel()
    if settings.llm_provider == "mistral":
        if not settings.mistral_api_key:
            msg = "LLM_PROVIDER=mistral requires MISTRAL_API_KEY"
            raise RuntimeError(msg)
        model = {
            "translate": settings.model_translate,
            "categorize": settings.model_categorize,
            "summarize": settings.model_summarize,
            "evaluate": settings.model_evaluator,
        }.get(task, settings.model_translate)
        return OpenAICompatibleChatModel(
            base_url=settings.mistral_base_url,
            api_key=settings.mistral_api_key,
            model=model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            json_mode=task in {"translate", "categorize", "evaluate"},
        )
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            msg = "LLM_PROVIDER=openai requires OPENAI_API_KEY"
            raise RuntimeError(msg)
        return OpenAICompatibleChatModel(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.model_openai,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            json_mode=task in {"translate", "categorize", "evaluate"},
        )
    msg = f"Unknown llm_provider: {settings.llm_provider}"
    raise ValueError(msg)


def build_embeddings(settings: Settings) -> Embeddings:
    if settings.embedding_provider == "stub":
        return StubEmbeddings(dim=settings.embedding_dim)
    if settings.embedding_provider == "mistral":
        if not settings.mistral_api_key:
            msg = "EMBEDDING_PROVIDER=mistral requires MISTRAL_API_KEY"
            raise RuntimeError(msg)
        return OpenAICompatibleEmbeddings(
            base_url=settings.mistral_base_url,
            api_key=settings.mistral_api_key,
            model=settings.mistral_embedding_model,
            timeout=settings.embedding_timeout_seconds,
        )
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            msg = "EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY"
            raise RuntimeError(msg)
        return OpenAICompatibleEmbeddings(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model="text-embedding-3-small",
            timeout=settings.embedding_timeout_seconds,
        )
    msg = f"Unknown embedding_provider: {settings.embedding_provider}"
    raise ValueError(msg)


def build_chat_models(settings: Settings) -> dict[str, BaseChatModel]:
    return {task: build_chat_model(settings, task) for task in ("translate", "categorize", "summarize", "evaluate")}
