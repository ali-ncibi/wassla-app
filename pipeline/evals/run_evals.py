import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from app.config import Settings, get_settings
from app.observability import setup_tracing

setup_tracing(get_settings())

from app.feeds import FeedItem
from app.graph.nodes import Deps, call_llm, parse_json_object
from app.graph.pipeline import build_article_graph
from app.graph.prompts import evaluate_messages
from app.providers import build_chat_models, build_embeddings

DATASET_NAME = "wassla-article-evals"
DATASET_PATH = Path(__file__).parent / "dataset.jsonl"
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
MAX_SUMMARY_WORDS = 150


def item_from_dict(d: dict[str, Any]) -> FeedItem:
    d = dict(d)
    pa = d.get("published_at")
    if isinstance(pa, str):
        d["published_at"] = datetime.fromisoformat(pa)
    return FeedItem(**d)  # type: ignore[arg-type]


def load_examples(path: Path) -> list[dict[str, Any]]:
    examples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            examples.append(json.loads(line))
    return examples


def make_deps(settings: Settings) -> Deps:
    return Deps(
        settings=settings,
        pool=cast("Any", None),
        chat=build_chat_models(settings),
        embedder=build_embeddings(settings),
        semaphore=asyncio.Semaphore(settings.llm_max_concurrency),
    )


async def make_task(deps: Deps) -> Any:
    graph = build_article_graph(deps, persist=False)

    async def task(input: dict[str, Any]) -> dict[str, Any]:
        from openinference.instrumentation import using_tags

        item = item_from_dict(input["item"])
        with using_tags(["eval"]):
            result = await graph.ainvoke(
                {"item": item},
                config={"tags": ["eval"], "run_name": "eval-article"},
            )
        return {
            "category": result["category"],
            "translations": result["translations"],
            "summaries": result["summaries"],
            "evaluation": result["evaluation"],
        }

    return task


def eval_category_matches(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    ok = output["category"] == expected["expected_category"]
    return {"score": 1.0 if ok else 0.0, "label": "pass" if ok else f"got {output['category']!r}"}


def eval_all_languages_present(output: dict[str, Any], metadata: dict[str, Any]) -> bool:
    langs = set(metadata["languages"])
    return set(output["translations"]) == langs and set(output["summaries"]) == langs


def eval_summary_length(output: dict[str, Any]) -> bool:
    return all(len(s.split()) <= MAX_SUMMARY_WORDS for s in output["summaries"].values())


def eval_arabic_script(output: dict[str, Any], metadata: dict[str, Any]) -> bool:
    if "ar" not in metadata["languages"]:
        return True
    tr = output["translations"]["ar"]
    return bool(ARABIC_RE.search(tr["title"] + " " + tr["body"]))


def eval_score_shape(output: dict[str, Any]) -> bool:
    ev = output["evaluation"]
    return 0.0 <= float(ev["score"]) <= 10.0 and ev["verdict"] in {"pass", "review"}


def make_judge_evaluator(deps: Deps) -> Any:
    """LLM-as-judge reusing the pipeline's EVALUATION TASK rubric; needs a real LLM provider."""

    async def judge(output: dict[str, Any], input: dict[str, Any]) -> dict[str, Any]:
        item = item_from_dict(input["item"])
        original = {"title": item.title, "body": item.body[:2000]}
        out = await call_llm(
            deps,
            "evaluate",
            evaluate_messages(
                item.source_language,
                original,
                output["translations"],
                output["summaries"],
                output["category"],
            ),
        )
        data = parse_json_object(out)
        score = max(0.0, min(10.0, float(data.get("score", 0))))
        return {"score": score / 10.0, "label": str(data.get("verdict", "?"))}

    return judge


async def run_on_phoenix(
    settings: Settings,
    examples: list[dict[str, Any]],
    task: Any,
    evaluators: list[Any],
) -> None:
    from phoenix.client import AsyncClient

    base_url = settings.phoenix_collector_endpoint.removesuffix("/v1/traces")
    client = AsyncClient(base_url=base_url)
    try:
        dataset = await client.datasets.get_dataset(dataset=DATASET_NAME)
        print(f"reusing existing Phoenix dataset {DATASET_NAME!r}")
    except Exception:
        dataset = await client.datasets.create_dataset(
            name=DATASET_NAME,
            examples=examples,
            dataset_description="Golden RSS items for the wassla article agent graph",
        )
        print(f"created Phoenix dataset {DATASET_NAME!r} with {len(examples)} examples")
    experiment = await client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=evaluators,
        experiment_name=f"article-evals-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        print_summary=True,
    )
    exp_id = (
        (experiment.get("id") or experiment.get("experiment_id")) if isinstance(experiment, dict) else experiment.id
    )
    print(f"experiment {exp_id or '?'} done, see http://localhost:6006 > Datasets > {DATASET_NAME} > Experiments")


async def amain() -> int:
    settings = get_settings()
    deps = make_deps(settings)
    examples = load_examples(DATASET_PATH)
    if not examples:
        msg = f"no examples in {DATASET_PATH}"
        raise SystemExit(msg)

    task = await make_task(deps)
    evaluators: list[Any] = [eval_all_languages_present, eval_summary_length, eval_score_shape]
    if settings.llm_provider != "stub":
        evaluators = [
            eval_category_matches,
            eval_all_languages_present,
            eval_arabic_script,
            eval_summary_length,
            eval_score_shape,
            make_judge_evaluator(deps),
        ]
    else:
        print("LLM_PROVIDER=stub: running structural evals only (category/script/judge need a real provider)")

    await run_on_phoenix(settings, examples, task, evaluators)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main()
