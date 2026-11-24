"""Run paired, retrieval-only evaluation on a fixed sample of QASPER test v0.3."""

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tarfile
import time
import unicodedata

from .__main__ import PROJECT, ROOT, file_sha256, load_fixture

ARCHIVE_NAME = "qasper-test-and-evaluator-v0.3.tgz"
ARCHIVE_URL = f"https://qasper-dataset.s3.us-west-2.amazonaws.com/{ARCHIVE_NAME}"
ARCHIVE_SHA256 = "72a52a41193e2838b8074f80ac074b94f956b84886c36a61c58a7df4171bdd72"
TEST_FILENAME = "qasper-test-v0.3.json"
SAMPLE_SIZE = 24
SAMPLE_SEED = "YourNote-QASPER-test-v0.3-2026-11-24"


def load_test(archive):
    if archive.stat().st_size != 3_865_061 or file_sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("Archive does not match the published QASPER v0.3 test checksum.")
    with tarfile.open(archive, "r:gz") as tar:
        members = [info for info in tar if info.isfile() and Path(info.name).name == TEST_FILENAME]
        if len(members) != 1:
            raise ValueError("Expected exactly one official QASPER test JSON member.")
        with tar.extractfile(members[0]) as stream:
            return json.load(stream)


def paragraph_text(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def sample_key(kind, *identifiers):
    return hashlib.sha256("\0".join((SAMPLE_SEED, kind, *identifiers)).encode()).hexdigest()


def sample_cases(papers):
    """Select one eligible case per paper, by ID hash, before retrieval."""
    eligible_papers = []
    eligible_questions = 0
    for paper_id, paper in papers.items():
        paragraphs = [
            text
            for section in paper["full_text"]
            for raw in section["paragraphs"]
            if (text := paragraph_text(raw))
        ]
        paragraph_positions = defaultdict(list)
        for index, paragraph in enumerate(paragraphs, start=1):
            paragraph_positions[paragraph].append(index)

        candidates = []
        for qa in paper["qas"]:
            references = []
            for annotation in qa["answers"]:
                answer = annotation["answer"]
                evidence = [paragraph_text(text) for text in answer["evidence"]]
                if (answer["unanswerable"] or not evidence or
                        any(len(paragraph_positions.get(text, ())) != 1 for text in evidence)):
                    break
                references.append(sorted({paragraph_positions[text][0] for text in evidence}))
            if references and len(references) == len(qa["answers"]):
                candidates.append({"question_id": qa["question_id"], "question": qa["question"],
                                   "gold_paragraph_sets": references})
        eligible_questions += len(candidates)
        if candidates:
            choice = min(candidates, key=lambda case: sample_key("question", paper_id, case["question_id"]))
            eligible_papers.append((paper_id, paragraphs, choice))

    eligible_papers.sort(key=lambda item: sample_key("paper", item[0]))
    selected = eligible_papers[:SAMPLE_SIZE]
    if len(selected) != SAMPLE_SIZE:
        raise ValueError(f"The test release must contain at least {SAMPLE_SIZE} eligible papers.")
    return selected, {"eligible_papers": len(eligible_papers), "eligible_questions": eligible_questions}


def evidence_metrics(predicted, references):
    retrieved = set(predicted)
    overlaps = [(len(retrieved.intersection(ref)), len(ref)) for ref in references]
    return {
        "hit_at_5": int(any(found for found, _ in overlaps)),
        "recall_at_5": max(found / total for found, total in overlaps),
        "evidence_f1_at_5": max(2 * found / (len(retrieved) + total) for found, total in overlaps),
    }


def run_retrieval(selected, policy):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    from evaluation.phase06.bundle import isolated_index
    from src.config import settings
    from src.grounding import verify_citation
    from src.rag import format_citations, retrieve, retrieve_vector

    keys = ("embedding_model", "chunk_size", "chunk_overlap")
    for key in keys:
        if getattr(settings, key) != policy[key]:
            raise ValueError(f"Active {key} differs from the evaluation policy.")

    fixture = {
        "sources": [
            {"id": paper_id, "filename": f"qasper-{sample_key('file', paper_id)[:16]}.txt",
             "format": "text", "blocks": paragraphs}
            for paper_id, paragraphs, _ in selected
        ],
        "license_notice": (
            "Source: QASPER (Dasigi et al., NAACL 2021), https://allenai.org/data/qasper. "
            "Dataset license: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/. "
            "Papers keep their source license. This evaluation uses the textual body only, "
            "with whitespace and Unicode normalized. Temporary local copies.\n"
        ),
    }
    rows = []
    start = time.perf_counter()
    with isolated_index(fixture=fixture) as mapping:
        init_seconds = time.perf_counter() - start
        arms = (("hybrid", retrieve), ("vector", retrieve_vector))
        for index, (paper_id, paragraphs, case) in enumerate(selected):
            source = mapping[paper_id]
            scope = {"filenames": [source["filename"]],
                     "document_versions": {source["filename"]: source["document_version"]}}
            for arm, search in (arms if index % 2 == 0 else reversed(arms)):
                query_start = time.perf_counter()
                chunks = search(case["question"], k=policy["k"], filters=scope)
                retrieval_ms = (time.perf_counter() - query_start) * 1000
                for chunk in chunks:
                    metadata = chunk.metadata
                    if (metadata.filename != source["filename"] or
                            metadata.document_version != source["document_version"] or
                            metadata.locator is None or
                            metadata.locator.kind != "paragraph" or
                            not 1 <= metadata.locator.paragraph <= len(paragraphs)):
                        raise ValueError(f"Invalid scope or locator for {case['question_id']}.")
                for citation in format_citations(chunks):
                    verify_citation(citation)
                predicted = list(dict.fromkeys(chunk.metadata.locator.paragraph for chunk in chunks))
                rows.append({"paper_id": paper_id, "question_id": case["question_id"],
                             "retriever": arm, "retrieved_paragraphs": predicted,
                             "source_sha256": source["document_version"], "locator_checks": len(chunks),
                             "retrieval_ms": retrieval_ms, **evidence_metrics(predicted, case["gold_paragraph_sets"])})
    summary = {}
    for arm, _ in arms:
        group = [row for row in rows if row["retriever"] == arm]
        summary[arm] = {
            "questions": len(group),
            "hits": sum(row["hit_at_5"] for row in group),
            "macro_recall_at_5": statistics.mean(row["recall_at_5"] for row in group),
            "macro_evidence_f1_at_5": statistics.mean(row["evidence_f1_at_5"] for row in group),
            "locator_checks": sum(row["locator_checks"] for row in group),
        }
    return {"init_seconds": init_seconds, "summary": summary, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog=f"Official test archive: {ARCHIVE_URL}")
    parser.add_argument("archive", type=Path, help=ARCHIVE_NAME)
    parser.add_argument("--preview", action="store_true", help="Show the fixed case manifest without running retrieval")
    args = parser.parse_args()
    try:
        _, policy = load_fixture()
        papers = load_test(args.archive)
        selected, pool = sample_cases(papers)
        cases = [
            {"paper_id": paper_id, "question_id": case["question_id"],
             "gold_paragraph_sets": case["gold_paragraph_sets"], "document_paragraphs": len(paragraphs)}
            for paper_id, paragraphs, case in selected
        ]
        manifest = json.dumps(cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        results = {
            "dataset": "QASPER v0.3, official test split, text-only answerable sample",
            "dataset_archive_sha256": ARCHIVE_SHA256,
            "sampling_seed": SAMPLE_SEED,
            "base_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
            "retrieval_code_sha256": {
                name: file_sha256(PROJECT / name) for name in (
                    "evaluation/phase07/qasper.py", "evaluation/phase06/bundle.py", "src/rag.py",
                    "src/retrieval.py", "src/document_parser.py", "src/indexing.py", "src/embeddings.py",
                )
            },
            "policy_sha256": file_sha256(ROOT / "policy.json"),
            "configuration": {
                key: policy[key] for key in ("k", "embedding_model", "chunk_size", "chunk_overlap")
            },
            "llm_calls": 0, **pool,
            "case_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "cases": cases,
        }
        if not args.preview:
            results.update(run_retrieval(selected, policy))
    except (ValueError, OSError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"QASPER: {exc}\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
