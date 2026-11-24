"""Export blinded review material and aggregate completed rubric labels."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from evaluation.phase07.__main__ import load_fixture, require
from evaluation.phase08.benchmark import clean_ratio, inference_summary, partition, write_new


def make_packet(inference, fixture):
    cases = {case["id"]: case for case in fixture["cases"] + fixture["pilot_cases"]}
    items, key, template = [], {}, {}
    for row in inference["rows"]:
        if row["status"] != "completed":
            continue
        case = cases[row["case_id"]]
        raw_id = f'{inference["plan_sha256"]}/{row["case_id"]}/{row["retriever"]}'
        blind_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
        key[blind_id] = {"case_id": row["case_id"], "retriever": row["retriever"], "split": row["split"]}
        required = {f"G{index}": claim for index, claim in enumerate(case["required_claims"], 1)}
        items.append({
            "blind_id": blind_id, "split": row["split"], "question": case["question"],
            "referent": case["referent"], "history": case["history"], "required_claims": required,
            "reference_evidence": case["expected_evidence"], "information_missing": case["missing"],
            "expected_behavior": case["expected_behavior"], "answer": row["answer"],
            "context": row["retrieval"]["context"], "citations": row["citations"],
        })
        template[blind_id] = {"required_claim_covered": dict.fromkeys(required), "claims": [],
                              "unassigned_markers": [], "uncertainty_correct": None, "strict_pass": None, "notes": ""}
    items.sort(key=lambda item: (item["split"] != "pilot", item["blind_id"]))
    return items, key, {item["blind_id"]: template[item["blind_id"]] for item in items}


def validated_labels(review, template, blind_rows):
    require(review["reviewer_id"].strip() and review["role"] in {"human", "developer_agent", "adjudicated"},
            "A valid reviewer ID and role are required.")
    labels = {}
    for blind_id, label in review["labels"].items():
        require(blind_id in template, "Review contains an unknown blinded ID.")
        if label["strict_pass"] is None:
            continue
        require(type(label["strict_pass"]) is bool and type(label["uncertainty_correct"]) is bool,
                f"{blind_id}: per-answer decisions must be true or false.")
        required = label["required_claim_covered"]
        require(required.keys() == template[blind_id]["required_claim_covered"].keys()
                and all(type(value) is bool for value in required.values()), f"{blind_id}: incomplete required-claim labels.")
        claims = label["claims"]
        require(len({claim["claim_id"] for claim in claims}) == len(claims), f"{blind_id}: repeated claim IDs.")
        assigned = set()
        valid = {citation["source_marker"] for citation in blind_rows[blind_id]["citations"]}
        for claim in claims:
            markers = claim["marker_contributions"]
            require(claim["claim_text"].strip()
                    and all(type(claim[key]) is bool for key in ("supported_by_context", "supported_by_citations"))
                    and all(type(value) is bool for value in markers.values()), f"{blind_id}: invalid claim labels.")
            require(markers.keys() <= valid, f"{blind_id}: unknown marker.")
            require(not claim["supported_by_citations"] or claim["supported_by_context"],
                    f"{blind_id}: cited paragraphs must come from the context.")
            require(claim["supported_by_citations"] == any(markers.values()),
                    f"{blind_id}: marker contributions contradict citation coverage.")
            assigned.update(markers)
        unassigned = label["unassigned_markers"]
        require(len(unassigned) == len(set(unassigned)) and set(unassigned) == valid - assigned,
                f"{blind_id}: missing or duplicate unassigned markers.")
        require(not label["strict_pass"] or (
            all(required.values()) and label["uncertainty_correct"]
            and all(claim["supported_by_citations"] for claim in claims) and not unassigned
        ), f"{blind_id}: strict pass contradicts underlying labels.")
        labels[blind_id] = label
    return labels


def summarize_review(rows, labels, key):
    id_by_case = {(item["case_id"], item["retriever"]): blind_id for blind_id, item in key.items()}
    completed = [row for row in rows if row["status"] == "completed"]
    reviewed = [labels[blind_id] for row in completed
                if (blind_id := id_by_case[(row["case_id"], row["retriever"])]) in labels]
    attempted = sum(row["status"] != "not_run" for row in rows)
    passed = sum(label["strict_pass"] for label in reviewed)
    pending = len(completed) - len(reviewed)
    required = [value for label in reviewed for value in label["required_claim_covered"].values()]
    claims = [claim for label in reviewed for claim in label["claims"]]
    contributions = [value for claim in claims for value in claim["marker_contributions"].values()]
    extra = sum(len(label["unassigned_markers"]) for label in reviewed)
    return {
        **inference_summary(rows),
        "reviewed": len(reviewed), "review_pending": pending, "strict_pass_count": passed,
        "strict_pass_rate": clean_ratio(passed, attempted) if not pending else None,
        "required_claim_coverage": clean_ratio(sum(required), len(required)),
        "faithfulness": clean_ratio(sum(item["supported_by_context"] for item in claims), len(claims)),
        "citation_recall": clean_ratio(sum(item["supported_by_citations"] for item in claims), len(claims)),
        "citation_precision": clean_ratio(sum(contributions), len(contributions) + extra),
        "uncited_claims": sum(not item["marker_contributions"] for item in claims),
        "uncertainty_correct": clean_ratio(sum(label["uncertainty_correct"] for label in reviewed), len(reviewed)),
    }


def agreement(a, b, key):
    counts = Counter(
        (a[blind_id]["strict_pass"], b[blind_id]["strict_pass"])
        for blind_id in a.keys() & b.keys() if key[blind_id]["split"] == "main"
    )
    samples = sum(counts.values())
    matches = counts[True, True] + counts[False, False]
    expected = (
        (counts[True, True] + counts[True, False]) * (counts[True, True] + counts[False, True])
        + (counts[False, True] + counts[False, False]) * (counts[True, False] + counts[False, False])
    )
    return {
        "agreement": clean_ratio(matches, samples),
        "cohens_kappa": (matches * samples - expected) / (samples * samples - expected)
        if samples * samples != expected else None,
        "contingency": {"both_pass": counts[True, True], "first_only": counts[True, False],
                        "second_only": counts[False, True], "both_fail": counts[False, False]},
    }


def paired_review(rows, labels, key):
    id_by_case = {(item["case_id"], item["retriever"]): blind_id for blind_id, item in key.items()}
    indexed = {(row["case_id"], row["retriever"]): row for row in rows if row["split"] == "main"}
    pairs = []
    for (case_id, arm), vector in indexed.items():
        if arm != "vector":
            continue
        hybrid = indexed[case_id, "hybrid"]
        pair = {"case_id": case_id, "hybrid_status": hybrid["status"], "vector_status": vector["status"]}
        if hybrid["status"] == vector["status"] == "completed":
            hm, vm = hybrid["actual_model"], vector["actual_model"]
            pair.update(hybrid_model=hm, vector_model=vm, comparable=bool(hm and hm == vm))
            if pair["comparable"]:
                for branch in ("hybrid", "vector"):
                    item = labels.get(id_by_case[case_id, branch])
                    pair[branch + "_strict_pass"] = item["strict_pass"] if item else None
        else:
            pair["comparable"] = False
        pairs.append(pair)
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inference", type=Path)
    parser.add_argument("directory", type=Path, help="New output directory")
    parser.add_argument("--labels", type=Path, action="append", default=[])
    args = parser.parse_args()

    fixture, _ = load_fixture()
    inference = json.loads(args.inference.read_bytes())
    packet, key, template = make_packet(inference, fixture)
    if not args.labels:
        args.directory.mkdir(parents=True, exist_ok=False)
        write_new(args.directory / "blinded_packet.json", {"items": packet})
        write_new(args.directory / "private_key.json", {"items": key})
        write_new(args.directory / "review_template.json", {"reviewer_id": "", "role": "human", "labels": template})
        return 0

    reviews = [json.loads(path.read_bytes()) for path in args.labels]
    require(len({review["reviewer_id"] for review in reviews}) == len(reviews), "Reviewer IDs must be distinct.")
    by_case = {(row["case_id"], row["retriever"]): row for row in inference["rows"]}
    blind_rows = {blind_id: by_case[item["case_id"], item["retriever"]] for blind_id, item in key.items()}
    labels = [validated_labels(review, template, blind_rows) for review in reviews]
    independent = [(review, label) for review, label in zip(reviews, labels) if review["role"] == "human"]
    overlap = (agreement(independent[0][1], independent[1][1], key) if len(independent) == 2 else None)
    output = {
        "human_reviewer_count": len(independent),
        "inter_rater": overlap,
        "reviewers": [
            {"reviewer_id": review["reviewer_id"], "role": review["role"],
             "metrics": {name: summarize_review(rows, label, key)
                         for name, rows in partition(inference["rows"]).items()},
             "pairs": paired_review(inference["rows"], label, key)}
            for review, label in zip(reviews, labels)
        ],
    }
    args.directory.mkdir(parents=True, exist_ok=False)
    write_new(args.directory / "scores.json", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
