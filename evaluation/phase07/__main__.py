"""Check Phase 07 materials or preview a run. Neither command calls an LLM."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from evaluation.phase06.bundle import write_materials

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
PROMPT = PROJECT / "src/prompts/answer.jinja2"
FORMATS = {".pdf": "pdf", ".docx": "docx", ".md": "markdown", ".txt": "text"}
GROUPS = ("single_source", "multi_source", "insufficient", "follow_up")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def file_sha256(path):
    return sha256(path.read_bytes())


def validate_case(case, sources):
    case_id = case["id"]
    scope = set(case["sources"])
    require(scope and scope <= sources.keys() and len(scope) == len(case["sources"]),
            f"{case_id}: invalid source scope")
    require(case["question"].strip() and case["group"] in GROUPS and case["expected_behavior"].strip(),
            f"{case_id}: missing case instructions")
    if case["pages"]:
        require(len(case["pages"]) == 1 and len(scope) == 1, f"{case_id}: page scope must select one PDF")
        source = sources[case["sources"][0]]
        require(source["format"] == "pdf" and 1 <= case["pages"][0] <= len(source["pages"]),
                f"{case_id}: unknown PDF page")

    answerability = {
        "full": (True, False, True),
        "partial": (True, True, True),
        "none": (False, True, False),
    }
    actual = tuple(bool(case[key]) for key in ("required_claims", "missing", "expected_evidence"))
    require(answerability.get(case["answerability"]) == actual, f"{case_id}: inconsistent answerability")
    require((case["group"] == "insufficient") == bool(case["missing"]),
            f"{case_id}: inconsistent missing evidence group")
    require(len(scope) == 1 if case["group"] == "single_source" else
            len(scope) >= 2 if case["group"] == "multi_source" else True,
            f"{case_id}: wrong number of selected sources for group")
    if case["group"] == "multi_source":
        require({ref["source"] for ref in case["expected_evidence"]} == scope,
                f"{case_id}: expected evidence must cover every selected source")

    follow_up = case["group"] == "follow_up"
    require(follow_up == bool(case["history"]) == bool(case["referent"]),
            f"{case_id}: history or referent missing/misplaced")
    for turn in case["history"]:
        require(turn["status"] == "completed" and turn["question"].strip() and turn["answer"].strip()
                and turn["sources"] and set(turn["sources"]) <= scope,
                f"{case_id}: prior turn is incomplete or out of scope")

    require(len({digest(ref) for ref in case["expected_evidence"]}) == len(case["expected_evidence"]),
            f"{case_id}: duplicate evidence unit")
    for ref in case["expected_evidence"]:
        source_id = ref["source"]
        locator = ref["locator"]
        require(source_id in scope and ref["quote"].strip(), f"{case_id}: evidence outside scope or empty")
        if sources[source_id]["format"] == "pdf":
            require(locator.keys() == {"kind", "page"} and locator["kind"] == "page" and
                    1 <= locator["page"] <= len(sources[source_id]["pages"]),
                    f"{case_id}: invalid PDF locator")
            require(not case["pages"] or locator["page"] in case["pages"], f"{case_id}: evidence outside page scope")
        else:
            require(locator.keys() == {"kind", "paragraph", "anchor"} and locator["kind"] == "paragraph" and
                    1 <= locator["paragraph"] <= len(sources[source_id]["blocks"]) and
                    locator["anchor"] == f"b{locator['paragraph']:06}",
                    f"{case_id}: invalid paragraph locator")


def load_fixture():
    """Load the frozen case set and verify its relationship to the run policy."""
    raw = (ROOT / "fixture.json").read_bytes()
    fixture = json.loads(raw)
    policy = json.loads((ROOT / "policy.json").read_bytes())
    require(fixture["schema_version"] == policy["schema_version"] == 1, "Unknown schema version")
    require(sha256(raw) == policy["fixture_sha256"], "Fixture changed. Freeze a new evaluation version.")
    require(file_sha256(PROMPT) == policy["prompt_sha256"], "Answer prompt changed. Freeze a new evaluation version.")
    require(digest(policy["rubric"]) == policy["rubric_sha256"], "Rubric hash mismatch")
    require(fixture["license"] == "CC0-1.0", "Unexpected material license")
    sources = {source["id"]: source for source in fixture["sources"]}
    require(4 <= len(sources) <= 6 and len(sources) == len(fixture["sources"]), "Invalid source count or duplicate source")
    filenames = {source["filename"] for source in sources.values()}
    require(len(filenames) == len(sources), "Duplicate material filename")
    for source in sources.values():
        filename = source["filename"]
        require(Path(filename).name == filename and FORMATS.get(Path(filename).suffix) == source["format"],
                f"Invalid material filename or format: {filename}")

    require(set(policy["source_sha256"]) == sources.keys(), "Material checksums do not cover exactly the source set")
    main = fixture["cases"]
    pilot = fixture["pilot_cases"]
    all_cases = main + pilot
    require(Counter(case["group"] for case in main) == dict.fromkeys(GROUPS, 6), "Incorrect main-group counts")
    require(len(pilot) == policy["pilot_max_calls"] == 3, "Invalid pilot count or budget")
    require(len({case["id"] for case in all_cases}) == len(all_cases), "Duplicate case ID")
    require(len({case["question"].strip() for case in all_cases}) == len(all_cases), "Duplicate question")
    main_refs = {digest(ref) for case in main for ref in case["expected_evidence"]}
    pilot_refs = {digest(ref) for case in pilot for ref in case["expected_evidence"]}
    require(main_refs.isdisjoint(pilot_refs), "Pilot and main share gold evidence units")
    for case in all_cases:
        validate_case(case, sources)

    groups_by_id = {case["id"]: case["group"] for case in main}
    pairs = policy["comparison_pairs"]
    pair_ids = {pair["case_id"] for pair in pairs}
    require(len(pair_ids) == len(pairs) == 8 and pair_ids <= groups_by_id.keys(), "Invalid paired cases")
    require(Counter(groups_by_id[case_id] for case_id in pair_ids) == dict.fromkeys(GROUPS, 2),
            "Each group needs two paired cases")
    require(Counter((groups_by_id[pair["case_id"]], pair["first"]) for pair in pairs) ==
            {(group, arm): 1 for group in GROUPS for arm in ("hybrid", "vector")},
            "Paired case order is not balanced within each group")
    require(len(main) + len(pairs) == policy["main_max_calls"] == 32, "Invalid main budget")
    return fixture, policy


def materialize(destination, fixture, policy):
    paths = write_materials(destination, fixture=fixture)
    for source_id, path in paths.items():
        require(file_sha256(path) == policy["source_sha256"][source_id],
                f"Generated file hash changed: {path.name}")
    return paths


def check(fixture, policy):
    """Parse generated files, ingest on a temporary index, and rank only the pilots."""
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    from evaluation.phase06.benchmark import retrieval
    from evaluation.phase06.bundle import case_history, case_scope, evidence_metrics, isolated_index
    from src.config import settings
    from src.conversation import contextual_query
    from src.document_parser import parse_file
    from src.grounding import normalized
    from src.rag import fetch_all_chunks

    for key in ("embedding_model", "chunk_size", "chunk_overlap"):
        require(getattr(settings, key) == policy[key], f"Active {key} differs from the frozen policy")

    with TemporaryDirectory(prefix="yournote-phase07-files-") as directory:
        paths = materialize(directory, fixture, policy)
        parsed = {name: parse_file(path) for name, path in paths.items()}
    documents = {}
    for source in fixture["sources"]:
        name = source["id"]
        document = parsed[name]
        require(source["format"] == document["kind"] and not document["warnings"], f"Could not cleanly parse {name}")
        units = len(source.get("pages", source.get("blocks")))
        require(len(document["blocks"]) == units, f"Unexpected parsed block count in {name}")
        documents[name] = {"filename": source["filename"], "blocks": units, "pages": document["page_count"],
                           "sha256": policy["source_sha256"][name]}

    case_checks = []
    pilot_rows = []
    with isolated_index(fixture=fixture) as mapping:
        for source_id, metadata in mapping.items():
            require(metadata["document_version"] == policy["source_sha256"][source_id],
                    f"Incorrect ingested version for {source_id}")
        for case in fixture["cases"] + fixture["pilot_cases"]:
            case_id = case["id"]
            for ref in case["expected_evidence"]:
                matches = [
                    block for block in parsed[ref["source"]]["blocks"]
                    if all(block["locator"].get(key) == value for key, value in ref["locator"].items())
                    and normalized(ref["quote"]) in normalized(block["text"])
                ]
                require(len(matches) == 1, f"{case_id}: gold evidence does not match a unique parsed locator")
            history = case_history(case, mapping)
            query = contextual_query(case["question"], history)
            require(not history or (query.endswith(case["question"]) and history[-1]["question"] in query
                                    and history[-1]["answer"] not in query),
                    f"{case_id}: follow-up does not use only intended prior questions")
            chunks = fetch_all_chunks(case_scope(case, mapping))
            metrics = evidence_metrics(case, chunks, mapping)
            require(chunks and metrics["scope_leaks"] == 0 and metrics["evidence_found"] == metrics["evidence_units"],
                    f"{case_id}: gold evidence missing from index or scope is incorrect")
            case_checks.append({"case_id": case_id, "scoped_chunks": len(chunks),
                                "gold_units_verified": metrics["evidence_found"], "scope_leaks": metrics["scope_leaks"]})

        for case in fixture["pilot_cases"]:
            for arm in (policy["primary_retriever"], policy["comparison_retriever"]):
                chunks, metrics = retrieval(case, mapping, arm, policy["k"])
                require(metrics["scope_leaks"] == metrics["invalid_marker_or_locator"] == 0,
                        f"{case['id']}: pilot scope or locator check failed")
                missing_evidence = [
                    ref for ref in case["expected_evidence"]
                    if not evidence_metrics({**case, "expected_evidence": [ref]}, chunks, mapping)["evidence_found"]
                ]
                pilot_rows.append({"case_id": case["id"], "retriever": arm,
                                   "missing_evidence": missing_evidence, **metrics})

    return {"main_cases": len(fixture["cases"]), "pilot_cases": len(fixture["pilot_cases"]),
            "documents": documents, "case_checks": case_checks, "pilot_retrieval": pilot_rows, "llm_calls": 0}


def preview(fixture, policy, *, provider, model, effort, split, max_calls):
    """Create deterministic jobs with a single requested model and explicit budget."""
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}", model), "Invalid model ID")
    require(max_calls >= 0, "Budget must be nonnegative")
    primary = policy["primary_retriever"]
    comparison = policy["comparison_retriever"]
    pair_first = {pair["case_id"]: pair["first"] for pair in policy["comparison_pairs"]}
    jobs = []
    if split in {"pilot", "all"}:
        jobs.extend({"split": "pilot", "case_id": case["id"], "retriever": primary}
                    for case in fixture["pilot_cases"])
    if split in {"main", "all"}:
        for case in fixture["cases"]:
            case_id = case["id"]
            arms = (comparison, primary) if pair_first.get(case_id) == comparison else (primary, comparison)
            jobs.append({"split": "main", "case_id": case_id, "retriever": arms[0]})
            if case_id in pair_first:
                jobs.append({"split": "main", "case_id": case_id, "retriever": arms[1]})
    approval = {
        "provider": provider, "model_requested": model, "effort_requested": effort,
        "split": split, "same_configuration_except_retriever": True,
        "base_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
        "evaluation_code_sha256": {
            name: file_sha256(PROJECT / name) for name in (
                "evaluation/phase07/__main__.py", "evaluation/phase06/bundle.py", "evaluation/phase06/benchmark.py",
                "src/rag.py", "src/conversation.py", "src/indexing.py", "src/document_parser.py",
            )
        },
        "fixture_sha256": policy["fixture_sha256"], "policy_sha256": file_sha256(ROOT / "policy.json"),
        "rubric_sha256": policy["rubric_sha256"], "prompt_sha256": policy["prompt_sha256"],
        "source_sha256": policy["source_sha256"], "k": policy["k"], "embedding_model": policy["embedding_model"],
        "chunk_size": policy["chunk_size"], "chunk_overlap": policy["chunk_overlap"],
        "max_model_calls": max_calls, "planned_model_calls_upper_bound": len(jobs),
        "automatic_retries": policy["automatic_retries"], "fits_budget": len(jobs) <= max_calls,
        "model_access_verified": False, "jobs": jobs,
    }
    return {**approval, "plan_sha256": digest(approval)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    actions.add_parser("check", help="Run the offline parser, temporary-index and pilot checks")
    export = actions.add_parser("materials", help="Generate the source files in a new directory")
    export.add_argument("directory", type=Path)
    plan = actions.add_parser("preview", help="Show the jobs and upper bound on paid LLM calls")
    plan.add_argument("--provider", choices=("chatgpt", "gemini"), default="chatgpt")
    plan.add_argument("--model", required=True)
    plan.add_argument("--effort")
    plan.add_argument("--split", choices=("main", "pilot", "all"), default="main")
    plan.add_argument("--max-calls", type=int, required=True)
    args = cli.parse_args()

    try:
        fixture, policy = load_fixture()
        if args.action == "materials":
            args.directory.mkdir(parents=True, exist_ok=False)
            paths = materialize(args.directory, fixture, policy)
            result = {"files": {key: str(path) for key, path in paths.items()}, "license": fixture["license"]}
        elif args.action == "check":
            result = check(fixture, policy)
        else:
            result = preview(fixture, policy, provider=args.provider, model=args.model,
                             effort=args.effort, split=args.split, max_calls=args.max_calls)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        cli.exit(1, f"Phase 07: {exc}\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.action == "preview" and not result["fits_budget"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
