import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.prompts import (
    ANSWER_SYSTEM,
    CATEGORIZE_SYSTEM,
    EVALUATE_SYSTEM,
    SUMMARIZE_SYSTEM,
    TRANSLATE_SYSTEM,
    UNTRUSTED_GUARD,
    answer_messages,
    categorize_messages,
    evaluate_messages,
    lang_name,
    summarize_messages,
    translate_messages,
)


def test_lang_name() -> None:
    assert lang_name("en") == "English"
    assert lang_name("fr") == "French"
    assert lang_name("ar") == "Arabic"
    assert lang_name("de") == "de"


def test_all_system_prompts_include_untrusted_guard() -> None:
    for prompt in (TRANSLATE_SYSTEM, CATEGORIZE_SYSTEM, SUMMARIZE_SYSTEM, EVALUATE_SYSTEM, ANSWER_SYSTEM):
        assert UNTRUSTED_GUARD in prompt


def test_translate_messages() -> None:
    msgs = translate_messages("ar", "Title", "Body text")
    assert isinstance(msgs[0], SystemMessage)
    assert isinstance(msgs[1], HumanMessage)
    assert "Target language: ar (Arabic)" in msgs[1].content
    assert "TITLE:\nTitle" in msgs[1].content
    assert "BODY:\nBody text" in msgs[1].content


def test_categorize_messages_embeds_categories_json() -> None:
    msgs = categorize_messages(["world", "sports"], "T", "B")
    assert '"world", "sports"' in msgs[1].content
    assert "BODY:\nB" in msgs[1].content


def test_summarize_messages_truncates_body() -> None:
    msgs = summarize_messages("fr", "T", "x" * 9000)
    assert "x" * 8000 in msgs[1].content
    assert "x" * 8001 not in msgs[1].content
    assert "Language: fr (French)" in msgs[1].content


def test_evaluate_messages_payload() -> None:
    msgs = evaluate_messages(
        "en",
        {"title": "T", "body": "B"},
        {"fr": {"title": "Tfr", "body": "Bfr"}},
        {"fr": "sum"},
        "world",
    )
    human = msgs[1].content
    assert isinstance(human, str)
    payload = json.loads(human.split("EVALUATION TASK\n", 1)[1])
    assert payload["source_language"] == "en"
    assert payload["original"] == {"title": "T", "body": "B"}
    assert payload["category"] == "world"
    assert payload["translations"]["fr"] == {"title": "Tfr", "summary": "sum"}


def test_answer_messages_numbers_context() -> None:
    msgs = answer_messages("ar", "question?", ["first", "second"])
    assert "Requested language: ar (Arabic)" in msgs[0].content
    assert "[1] first" in msgs[1].content
    assert "[2] second" in msgs[1].content
    assert "QUESTION:\nquestion?" in msgs[1].content
