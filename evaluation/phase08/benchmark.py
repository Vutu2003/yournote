"""Run the frozen Vietnamese QA benchmark, locally or with explicit plan approval."""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from importlib import metadata
import json
import math
import os
from pathlib import Path
import re
from statistics import median, mean
from tempfile import NamedTemporaryFile
from time import perf_counter
from unittest.mock import patch

from evaluation.phase06.bundle import case_history, case_scope, evidence_metrics, isolated_index
from evaluation.phase07.__main__ import PROJECT, digest, file_sha256, load_fixture, preview, require

PROTOCOL = PROJECT.parent / "results/phase_07_evaluation_design.md"
if not PROTOCOL.is_file():
    PROTOCOL = PROJECT / "results/phase_07_evaluation_design.md"
DEFAULT_ARTIFACTS = PROJECT / "evaluation/phase08/artifacts"
USAGE_FIELDS = ("input_tokens", "output_tokens", "total_tokens")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encode(data))


def checkpoint(path, data):
    """Preserve the last valid result if interrupted mid-write."""
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        name = Path(temp.name)
        temp.write(encode(data))
        temp.flush()
        os.fsync(temp.fileno())
    try:
        name.replace(path)
    finally:
        name.unlink(missing_ok=True)


def latency(values):
    ordered = sorted(values)
    return {"n": len(ordered), "median": median(ordered) if ordered else None,
            "p95": ordered[math.ceil(.95 * len(ordered)) - 1] if ordered else None}


def clean_ratio(number, denominator):
    return {"numerator": number, "denominator": denominator,
            "rate": number / denominator if denominator else None}


def make_plan(fixture, policy, directory, model=None, effort=None):
    from src.providers.contracts import GenerationParameters

    GenerationParameters(reasoning_effort=effort)
    count = policy["pilot_max_calls"] + policy["main_max_calls"]
    body = preview(fixture, policy, provider="chatgpt", model=model or "pending",
                   effort=effort, split="all", max_calls=count)
    body.pop("plan_sha256")
    sources = {source["id"]: source["filename"] for source in fixture["sources"]}
    cases = {case["id"]: case for case in fixture["pilot_cases"] + fixture["cases"]}
    body["jobs"] = [
        {**job, "question": cases[job["case_id"]]["question"], "group": cases[job["case_id"]]["group"],
         "sources": [sources[key] for key in cases[job["case_id"]]["sources"]],
         "source_ids": cases[job["case_id"]]["sources"], "pages": cases[job["case_id"]]["pages"]}
        for job in body["jobs"]
    ]
    body.update(
        model_requested=model,
        protocol_sha256=file_sha256(PROTOCOL),
        generation_parameters=asdict(GenerationParameters(reasoning_effort=effort)),
        package_versions={name: metadata.version(name) for name in (
            "httpx", "pypdf", "qdrant-client", "sentence-transformers", "torch")},
        output_paths={name: str(directory.resolve() / f"{name}.json")
                      for name in ("retrieval", "inference", "preflight")},
    )
    for name in ("evaluation/phase08/benchmark.py", "src/llm.py", "src/providers/chatgpt.py", "src/config.py",
                 "src/retrieval.py", "src/filters.py", "src/embeddings.py", "src/store.py", "src/grounding.py"):
        body["evaluation_code_sha256"][name] = file_sha256(PROJECT / name)
    return {**body, "plan_sha256": digest(body)}


@contextmanager
def benchmark_index(fixture, plan):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    import torch
    from src.config import settings
    from src.embeddings import _model

    torch.set_num_threads(2)
    for key in ("embedding_model", "chunk_size", "chunk_overlap"):
        require(getattr(settings, key) == plan[key], f"Active {key} differs from the frozen plan.")
    start = perf_counter()
    _model()
    embedding_seconds = perf_counter() - start
    start = perf_counter()
    with isolated_index(fixture=fixture) as mapping:
        require(all(mapping[source]["document_version"] == checksum for source, checksum in plan["source_sha256"].items()),
                "The ingested originals differ from the hashed materials.")
        init = {"embedding_initialization_seconds": embedding_seconds,
                "temporary_index_seconds": perf_counter() - start}
        yield mapping, init


class IntegrityError(ValueError):
    pass


def checked_context(case, mapping, arm, k):
    from src.conversation import contextual_query
    from src.grounding import verify_citation
    from src.rag import format_citations, retrieve, retrieve_vector

    scope = case_scope(case, mapping)
    history = case_history(case, mapping)
    query = contextual_query(case["question"], history)
    search = retrieve if arm == "hybrid" else retrieve_vector
    start = perf_counter()
    chunks = search(query, k=k, filters=scope)
    retrieval_ms = (perf_counter() - start) * 1000
    metrics = evidence_metrics(case, chunks, mapping)
    if metrics["scope_leaks"]:
        raise IntegrityError("scope_leak")
    try:
        citations = format_citations(chunks)
        for citation in citations:
            if verify_citation(citation) is None:
                raise ValueError("Missing source version.")
    except Exception as exc:
        raise IntegrityError("invalid_context_locator") from exc
    context = [citation.model_dump(exclude_none=True) for citation in citations]
    missing_evidence = [
        ref for ref in case["expected_evidence"]
        if not evidence_metrics({**case, "expected_evidence": [ref]}, chunks, mapping)["evidence_found"]
    ]
    result = {**metrics, "retrieval_ms": retrieval_ms, "query": query, "history": history,
              "locator_checks": len(citations), "missing_evidence": missing_evidence, "context": context}
    return chunks, result


def retrieval_summary(rows):
    completed = [row["retrieval"] for row in rows if row["status"] == "completed"]
    positive = [row for row in completed if row["evidence_hit"] is not None]
    return {
        "planned": len(rows), "completed": len(completed), "not_run": sum(row["status"] == "not_run" for row in rows),
        "evidence_hit_at_k": clean_ratio(sum(row["evidence_hit"] for row in positive), len(positive)),
        "macro_recall_at_k": clean_ratio(sum(row["evidence_recall"] for row in positive), len(positive)),
        "gold_units_retrieved": clean_ratio(sum(row["evidence_found"] for row in positive),
                                            sum(row["evidence_units"] for row in positive)),
        "locators_checked": sum(row["locator_checks"] for row in completed),
        "scope_leak_cases": sum(row.get("error_code") == "scope_leak" for row in rows),
        "invalid_context_locator_cases": sum(row.get("error_code") == "invalid_context_locator" for row in rows),
        "retrieval_ms": latency([row["retrieval_ms"] for row in completed]),
    }


def partition(rows):
    main = [row for row in rows if row["split"] == "main"]
    paired = {row["case_id"] for row in main if row["retriever"] == "vector"}
    hybrid = [row for row in main if row["retriever"] == "hybrid"]
    vector = [row for row in main if row["retriever"] == "vector"]
    sections = {"hybrid_main": hybrid, "hybrid_paired": [row for row in hybrid if row["case_id"] in paired],
                "vector_paired": vector, "pilot": [row for row in rows if row["split"] == "pilot"]}
    for arm, pool in (("hybrid", hybrid), ("vector", vector)):
        for group in dict.fromkeys(row["group"] for row in pool):
            sections[f"{arm}/{group}"] = [row for row in pool if row["group"] == group]
    return sections


def blank_rows(plan):
    return [{**job, "status": "not_run"} for job in plan["jobs"]]


def run_retrieval(fixture, plan):
    target = Path(plan["output_paths"]["retrieval"])
    rows = blank_rows(plan)
    output = {"observed_utc": utc_now(), "plan_sha256": plan["plan_sha256"], "k": plan["k"], "llm_calls": 0,
              "rows": rows, "initialization": None, "summary": None}
    write_new(target, output)
    cases = {case["id"]: case for case in fixture["cases"] + fixture["pilot_cases"]}
    with benchmark_index(fixture, plan) as (mapping, initialization):
        output["initialization"] = initialization
        for row in rows:
            row["status"] = "interrupted"
            checkpoint(target, output)
            try:
                case = cases[row["case_id"]]
                _, data = checked_context(case, mapping, row["retriever"], plan["k"])
                row.update(status="completed", retrieval=data)
            except IntegrityError as exc:
                row.update(status="error", error_code=str(exc))
                break
            except Exception as exc:
                row.update(status="error", error_code="retrieval_error", error_type=type(exc).__name__)
                break
            checkpoint(target, output)
    output["summary"] = {name: retrieval_summary(rows) for name, rows in partition(rows).items()}
    checkpoint(target, output)
    return int(any(row["status"] != "completed" for row in rows))


def active_catalog(manager):
    from src.errors import LLMErrorCode, LLMServiceError

    status = manager.status("phase08-benchmark")
    connection_id = status["active_connection_id"]
    profile = next((item for item in status["profiles"] if item["id"] == connection_id), None)
    if not profile or not profile["plan_enabled"]:
        raise LLMServiceError.for_code(LLMErrorCode.PERMISSION_REQUIRED)
    return connection_id, manager.catalog(connection_id)["models"]


@contextmanager
def count_generation_requests(before_send):
    """Count the production client's Responses attempts at the HTTP send boundary."""
    from src.providers import chatgpt

    new_client = chatgpt.new_client

    def instrumented():
        client = new_client()
        client.event_hooks["request"].append(before_send)
        return client

    with patch.object(chatgpt, "new_client", instrumented):
        yield


def inference_summary(rows):
    attempted = [row for row in rows if row["status"] != "not_run"]
    completed = [row for row in attempted if row["status"] == "completed"]
    provider_rows = [row for row in completed if row.get("model_calls", 0)]
    usage = {}
    for key in USAGE_FIELDS:
        counts = [(row.get("usage") or {}).get(key) for row in attempted if row.get("model_calls", 0)]
        usage[key] = sum(counts) if counts and all(count is not None for count in counts) else None
    return {
        "planned": len(rows), "attempted": len(attempted), "completed": len(completed),
        "not_run": len(rows) - len(attempted), "errors": len(attempted) - len(completed),
        "completion_rate": clean_ratio(len(completed), len(rows)),
        "model_calls": sum(row.get("model_calls", 0) for row in attempted),
        "response_seconds": latency([row["response_seconds"] for row in completed]),
        "provider_response_seconds": latency([row["response_seconds"] for row in provider_rows]),
        "local_no_call_completed": len(completed) - len(provider_rows), "reported_usage": usage,
        "citation_location": clean_ratio(sum(row.get("valid_citations", 0) for row in attempted),
                                         sum(row.get("citations_checked", 0) for row in attempted)),
        "completed_without_citation": sum(not row["citations"] for row in completed),
    }


def one_answer(manager, connection_id, plan, row, case, mapping, checkpoint_live):
    from src.errors import LLMErrorCode, LLMServiceError
    from src.grounding import verify_citation
    from src.llm import llm_task
    from src.providers.chatgpt import API_ROOT
    from src.providers.contracts import CancellationToken, CredentialRef, ExecutionContext, GenerationParameters, ModelSelection
    from src.rag import answer_from_chunks

    start = perf_counter()
    row.update(status="interrupted", model_calls=0, answer=None, citations=[], usage=None, actual_model=None)
    checkpoint_live()
    stage = "retrieval"
    try:
        chunks, row["retrieval"] = checked_context(case, mapping, row["retriever"], plan["k"])
        stage = "generation"
        context = ExecutionContext(ModelSelection("chatgpt", plan["model_requested"]), CredentialRef(connection_id),
                                   parameters=GenerationParameters(**plan["generation_parameters"]))
        cancellation = CancellationToken()

        def before_send(request):
            require(str(request.url) == API_ROOT + "/responses" and request.method == "POST",
                    "Unexpected inference endpoint.")
            require(row["model_calls"] == 0, "More than one send in a case.")
            row["model_calls"] += 1
            checkpoint_live()

        def record_generation(result):
            row.update(actual_model=result.model, usage=asdict(result.usage) if result.usage else None,
                       answer=result.text)

        with manager.bind_task(connection_id, cancellation) as resolver, count_generation_requests(before_send):
            with llm_task(context, credential_resolver=resolver, cancellation=cancellation,
                          on_result=record_generation, max_calls=1):
                answer = answer_from_chunks(case["question"], chunks, history=row["retrieval"]["history"])
        stage = "citation"
        row.update(answer=answer.answer,
                   citations=[citation.model_dump(exclude_none=True) for citation in answer.citations],
                   citations_checked=len(answer.citations), valid_citations=0)
        scope = case_scope(case, mapping)
        for citation in answer.citations:
            if (scope["document_versions"].get(citation.filename) != citation.document_version or
                    ("page" in scope and scope["page"] != citation.page)):
                continue
            try:
                row["valid_citations"] += int(verify_citation(citation) is not None)
            except ValueError:
                continue
        if row["citations_checked"] != row["valid_citations"]:
            raise IntegrityError("invalid_answer_locator")
        row["status"] = "completed"
    except IntegrityError as exc:
        row.update(status="error", error_stage=stage, error_code=str(exc))
    except LLMServiceError as exc:
        code = exc.code.value
        if stage == "generation" and exc.code == LLMErrorCode.INVALID_RESPONSE and row["answer"]:
            markers = set(re.findall(r"\[(S[1-9][0-9]*)\]", row["answer"]))
            available = {item["source_marker"] for item in row["retrieval"]["context"]}
            if not markers or not markers <= available:
                code = "invalid_answer_marker"
        row.update(status="error", error_stage=stage, error_code=code, error_http_status=exc.status_code)
    except Exception as exc:
        row.update(status="error", error_stage=stage, error_code="benchmark_error", error_type=type(exc).__name__)
    row["response_seconds"] = perf_counter() - start
    checkpoint_live()


def run_inference(fixture, plan):
    from backend.services.chatgpt_auth import get_manager, shutdown
    from src.errors import LLMServiceError

    target = Path(plan["output_paths"]["inference"])
    rows = blank_rows(plan)
    output = {"observed_utc": utc_now(), "plan_sha256": plan["plan_sha256"],
              "provider": plan["provider"], "model_requested": plan["model_requested"], "rows": rows,
              "catalog_verified": False, "initialization": None, "preflight_error": None,
              "pilot_transition": None, "summary": None}
    write_new(target, output)
    cases = {case["id"]: case for case in fixture["cases"] + fixture["pilot_cases"]}
    save = lambda: checkpoint(target, output)
    try:
        connection_id, models = active_catalog(manager := get_manager())
        entry = next((item for item in models if item["slug"] == plan["model_requested"]), None)
        require(entry is not None, "Requested model is absent from the verified ChatGPT catalog.")
        effort = plan["effort_requested"]
        require(not effort or effort in entry.get("supported_reasoning_levels", []), "Reasoning effort is unavailable.")
        output["catalog_verified"] = True
        with benchmark_index(fixture, plan) as (mapping, initialization):
            output["initialization"] = initialization
            for row in rows:
                if row["split"] == "main" and output["pilot_transition"] is None:
                    pilot_rows = [item for item in rows if item["split"] == "pilot"]
                    output["pilot_transition"] = {
                        "passed_technical_checks": all(item["status"] == "completed" for item in pilot_rows),
                        "semantic_rubric_excluded": True,
                    }
                    save()
                if sum(item.get("model_calls", 0) for item in rows) >= plan["max_model_calls"]:
                    break
                one_answer(manager, connection_id, plan, row, cases[row["case_id"]], mapping, save)
                print(json.dumps({"case_id": row["case_id"], "retriever": row["retriever"],
                                  "status": row["status"], "model_calls": row["model_calls"],
                                  "error_code": row.get("error_code")}), flush=True)
                if row["status"] != "completed":
                    break
    except LLMServiceError as exc:
        output["preflight_error"] = {"type": type(exc).__name__, "code": exc.code.value, "detail": exc.detail}
    except (OSError, ValueError) as exc:
        output["preflight_error"] = {"type": type(exc).__name__, "detail": str(exc)}
    finally:
        shutdown()
        output["summary"] = {name: inference_summary(rows) for name, rows in partition(rows).items()}
        save()
    return int(any(row["status"] != "completed" for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    freeze = actions.add_parser("plan")
    freeze.add_argument("--directory", type=Path, default=DEFAULT_ARTIFACTS)
    freeze.add_argument("--model")
    freeze.add_argument("--effort")
    for action in ("retrieval", "live"):
        command = actions.add_parser(action)
        command.add_argument("plan", type=Path)
        if action == "live":
            command.add_argument("--confirm-plan-sha", required=True)
    actions.add_parser("catalog")
    args = parser.parse_args()

    if args.action == "catalog":
        from backend.services.chatgpt_auth import get_manager, shutdown
        from src.errors import LLMServiceError

        try:
            _, models = active_catalog(get_manager())
            print(encode({"catalog_verified": True, "models": [item["slug"] for item in models]}))
        except LLMServiceError as exc:
            parser.exit(1, f"Phase 08 catalog: {exc.detail}\n")
        finally:
            shutdown()
        return 0

    fixture, policy = load_fixture()
    try:
        if args.action == "plan":
            plan = make_plan(fixture, policy, args.directory, args.model, args.effort)
            write_new(args.directory / "plan.json", plan)
            print(encode(plan), end="")
            return 0

        plan = json.loads(args.plan.read_bytes())
        expected = make_plan(fixture, policy, args.plan.parent, plan["model_requested"], plan["effort_requested"])
        require(plan == expected, "Frozen plan, inputs or benchmark code changed.")
        if args.action == "live":
            require(plan["model_requested"] and args.confirm_plan_sha == plan["plan_sha256"],
                    "Preview and approve the exact plan with an explicit ChatGPT model.")
            return run_inference(fixture, plan)
        return run_retrieval(fixture, plan)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Phase 08: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
