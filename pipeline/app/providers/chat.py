import json
import re
from collections.abc import Sequence
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def to_api_messages(messages: Sequence[BaseMessage]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages:
        role = "system" if isinstance(m, SystemMessage) else "assistant" if isinstance(m, AIMessage) else "user"
        content = m.content if isinstance(m.content, str) else json.dumps(m.content)
        out.append({"role": role, "content": content})
    return out


class OpenAICompatibleChatModel(BaseChatModel):
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.2
    timeout: float = 90.0
    json_mode: bool = False

    @property
    def _llm_type(self) -> str:
        return "openai-compatible-chat"

    def _generate(
        self,
        messages: Sequence[BaseMessage],
        stop: Sequence[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_api_messages(messages),
            "temperature": self.temperature,
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        usage_metadata = (
            {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
            if usage
            else None
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text, usage_metadata=usage_metadata))])


_CATEGORY_KEYWORDS = {
    "world": ["war", "gaza", "ukraine", "israel", "conflict", "diplomat", "border", "peace", "nato", "UN "],
    "politics": [
        "election",
        "parliament",
        "government",
        "minister",
        "president",
        "vote",
        "policy",
        "senate",
        "congress",
    ],
    "business": ["market", "stock", "inflation", "economy", "company", "oil", "bank", "trade", "gdp", "investor"],
    "technology": ["ai", "tech", "software", "chip", "app", "cyber", "robot", "startup", "data", "internet"],
    "science": ["study", "research", "scientists", "climate", "space", "nasa", "discovery", "journal"],
    "health": ["health", "hospital", "doctor", "disease", "virus", "vaccine", "who ", "medical"],
    "sports": ["football", "match", "olympic", "coach", "league", "champion", "fifa", "tennis", "goal"],
    "culture": ["film", "movie", "music", "art", "festival", "book", "museum", "celebrity"],
    "environment": ["climate", "emission", "green", "renewable", "pollution", "wildfire", "glacier", "environment"],
}


def _stub_reply(prompt: str, json_mode: bool) -> str:
    if "TRANSLATION TASK" in prompt:
        m = re.search(r"Target language: (\w+)", prompt)
        lang = m.group(1) if m else "xx"
        m_body = re.search(r"BODY:\n(.+)", prompt, re.S)
        excerpt = (m_body.group(1)[:400] if m_body else prompt[:400]).strip()
        title_m = re.search(r"TITLE:\n(.+)\n\nBODY:", prompt, re.S)
        title = title_m.group(1).strip() if title_m else "untitled"
        return json.dumps({"title": f"[{lang}] {title}", "body": f"[{lang}] {excerpt}"})
    if "CATEGORIZATION TASK" in prompt:
        low = prompt.lower()
        best, best_n = "world", 0
        for cat, kws in _CATEGORY_KEYWORDS.items():
            n = sum(low.count(k) for k in kws)
            if n > best_n:
                best, best_n = cat, n
        return json.dumps({"category": best, "confidence": 0.6})
    if "SUMMARIZATION TASK" in prompt:
        m_body = re.search(r"BODY:\n(.+)", prompt, re.S)
        text = m_body.group(1) if m_body else prompt
        return " ".join(text.split()[:60])
    if "EVALUATION TASK" in prompt:
        return json.dumps({"score": 8.0, "verdict": "pass", "issues": []})
    return "stub response"


class StubChatModel(BaseChatModel):
    model: str = "stub"
    json_mode: bool = False

    @property
    def _llm_type(self) -> str:
        return "stub-chat"

    def _generate(
        self,
        messages: Sequence[BaseMessage],
        stop: Sequence[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = "\n".join(m.content if isinstance(m.content, str) else json.dumps(m.content) for m in messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=_stub_reply(prompt, self.json_mode)))])
