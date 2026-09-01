"""
Round 4 stage 2: per-statement consensus statistics.

For each of the 40 statements, computes the rating distribution (excluding the
"Not qualified to respond" abstentions), median, IQR (Q3-Q1, linear
interpolation = R quantile type 7, verified to reproduce the Round 3 IQRs cited
in the manuscript), mean, SD, and the a-priori consensus classification
(IQR <= 1 consensus; 1 < IQR <= 1.5 near-consensus; IQR > 1.5 non-consensus).

Outputs consensus_stats.json and consensus_stats.csv into data/generated/.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ROUND4_RESPONSES,
    ROUND4_ANALYSIS_DIR,
    CONSENSUS_IQR_MAX,
    NEAR_CONSENSUS_IQR_MAX,
)
from r4_statements import R4_STATEMENTS, SECTION_NAMES, ordered_ids


def classify_consensus(iqr: float) -> str:
    if iqr <= CONSENSUS_IQR_MAX:
        return "consensus"
    if iqr <= NEAR_CONSENSUS_IQR_MAX:
        return "near-consensus"
    return "non-consensus"


def summarize_ratings(ratings: list) -> dict:
    """Summary statistics for a list of integer ratings (1-6, abstentions removed)."""
    arr = np.array(ratings, dtype=float)
    n = len(arr)
    distribution = {str(k): int(np.sum(arr == k)) for k in range(1, 7)}
    q1, q3 = (float(np.percentile(arr, 25)), float(np.percentile(arr, 75))) if n else (0.0, 0.0)
    iqr = round(q3 - q1, 4)
    return {
        "n_rated": n,
        "mean": round(float(np.mean(arr)), 4) if n else None,
        "std_dev": round(float(np.std(arr, ddof=1)), 4) if n > 1 else 0.0,
        "median": float(np.median(arr)) if n else None,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "min": int(np.min(arr)) if n else None,
        "max": int(np.max(arr)) if n else None,
        "distribution": distribution,
        "pct_agree": round(100.0 * float(np.mean(arr >= 4)), 1) if n else None,
        "consensus_class": classify_consensus(iqr) if n else "no-data",
    }


def compute_consensus(extracted_file: Path = None) -> dict:
    extracted_file = extracted_file or ROUND4_RESPONSES
    with open(extracted_file, encoding="utf-8") as f:
        data = json.load(f)

    # Gather per-statement ratings and abstention counts.
    ratings_by_id = {sid: [] for sid in R4_STATEMENTS}
    nq_by_id = {sid: 0 for sid in R4_STATEMENTS}
    for sub in data["submissions"]:
        for fb in sub["feedback"]:
            sid = fb["statement_id"]
            if fb.get("not_qualified"):
                nq_by_id[sid] += 1
            elif fb.get("rating") is not None:
                ratings_by_id[sid].append(int(fb["rating"]))

    statements = {}
    for sid in ordered_ids():
        meta = R4_STATEMENTS[sid]
        stats = summarize_ratings(ratings_by_id[sid])
        stats["n_not_qualified"] = nq_by_id[sid]
        statements[sid] = {
            "statement_id": sid,
            "section": meta["section"],
            "short_label": meta["short_label"],
            "statement_text": meta["text"],
            **stats,
        }

    # Section-level and overall consensus tallies.
    def tally(ids):
        t = {"consensus": 0, "near-consensus": 0, "non-consensus": 0}
        for sid in ids:
            t[statements[sid]["consensus_class"]] += 1
        return t

    section_summary = {
        sec: {"name": SECTION_NAMES[sec],
              "n_statements": sum(1 for s in R4_STATEMENTS.values() if s["section"] == sec),
              **tally([sid for sid in ordered_ids() if R4_STATEMENTS[sid]["section"] == sec])}
        for sec in ["A", "B", "C", "D"]
    }
    overall = tally(ordered_ids())

    result = {
        "metadata": {
            "round": 4,
            "n_participants": data["metadata"]["n_participants"],
            "n_statements": len(statements),
            "consensus_rule": "IQR<=1 consensus; 1<IQR<=1.5 near-consensus; IQR>1.5 non-consensus",
        },
        "overall": overall,
        "section_summary": section_summary,
        "statements": statements,
    }
    return result


def write_outputs(result: dict, output_dir: Path = None):
    output_dir = output_dir or ROUND4_ANALYSIS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "consensus_stats.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    csv_path = output_dir / "consensus_stats.csv"
    fields = ["statement_id", "section", "n_rated", "n_not_qualified", "mean", "std_dev",
              "median", "q1", "q3", "iqr", "min", "max", "pct_agree", "consensus_class",
              "short_label"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in ordered_ids():
            row = {k: result["statements"][sid].get(k) for k in fields}
            w.writerow(row)

    return json_path, csv_path


def main(extracted_file: Path = None, output_dir: Path = None):
    result = compute_consensus(extracted_file)
    json_path, csv_path = write_outputs(result, output_dir)

    o = result["overall"]
    print(f"[OK] Consensus stats -> {json_path}")
    print(f"     overall: {o['consensus']} consensus, {o['near-consensus']} near, "
          f"{o['non-consensus']} non-consensus (of {result['metadata']['n_statements']})")
    for sec, s in result["section_summary"].items():
        print(f"     Section {sec}: {s['consensus']}/{s['n_statements']} consensus, "
              f"{s['near-consensus']} near, {s['non-consensus']} non")
    return result


if __name__ == "__main__":
    main()
