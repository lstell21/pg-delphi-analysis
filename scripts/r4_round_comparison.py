"""
Round 4 stage 3: Round 3 vs Round 4 comparison and stability analysis.

For each Round 4 statement, recomputes the Round 3 median and IQR from the
stored Round 3 rating distributions (READ-ONLY) via the R3->R4 crosswalk
(pooling the distributions of merged Round 3 pairs), then reports:
  * Round 3 vs Round 4 median, IQR, and consensus class,
  * Delta median / Delta IQR,
  * stability (|Delta median| < 1 AND |Delta IQR| < 0.5),
  * movement toward / away from / unchanged consensus,
  * the stable non-consensus set (non-consensus in BOTH rounds).

Outputs data/generated/round3_vs_round4.json and .csv, and prints the
crosswalk with both rounds' figures for sign-off.

This is the only step that reads a Round 3 artifact, and it opens it read-only.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ROUND3_STATEMENT_ANALYSES,
    ROUND4_ANALYSIS_DIR,
    STABILITY_MEDIAN_MAX,
    STABILITY_IQR_MAX,
)
from r4_statements import R4_STATEMENTS, R4_TO_R3, SECTION_NAMES, ordered_ids
from r4_consensus_stats import compute_consensus, classify_consensus


def stats_from_distribution(dist: dict) -> dict:
    """Median, Q1, Q3, IQR, mean, n from a {rating: count} distribution."""
    vals = []
    for k, v in dist.items():
        vals.extend([int(k)] * int(v))
    arr = np.array(sorted(vals), dtype=float)
    n = len(arr)
    q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
    return {
        "n": n,
        "median": float(np.median(arr)),
        "q1": q1,
        "q3": q3,
        "iqr": round(q3 - q1, 4),
        "mean": round(float(np.mean(arr)), 4),
    }


def round3_stats_for(r4_id: str, r3_data: dict) -> dict:
    """Pooled Round 3 stats for the R3 source statement(s) of a R4 id."""
    pooled = {}
    for r3_id in R4_TO_R3[r4_id]:
        if r3_id not in r3_data:
            raise KeyError(f"Round 3 statement {r3_id} missing from {ROUND3_STATEMENT_ANALYSES}")
        dist = r3_data[r3_id]["rating_stats"]["distribution"]
        for k, v in dist.items():
            pooled[k] = pooled.get(k, 0) + int(v)
    stats = stats_from_distribution(pooled)
    stats["distribution"] = {str(k): int(pooled.get(str(k), 0)) for k in range(1, 7)}
    stats["consensus_class"] = classify_consensus(stats["iqr"])
    stats["source_ids"] = R4_TO_R3[r4_id]
    return stats


def movement(r3_class: str, r4_class: str) -> str:
    rank = {"consensus": 2, "near-consensus": 1, "non-consensus": 0}
    if rank[r4_class] > rank[r3_class]:
        return "toward consensus"
    if rank[r4_class] < rank[r3_class]:
        return "away from consensus"
    return "unchanged"


def compare(extracted_file: Path = None) -> dict:
    r4 = compute_consensus(extracted_file)["statements"]
    with open(ROUND3_STATEMENT_ANALYSES, encoding="utf-8") as f:
        r3_data = json.load(f)

    rows = {}
    for sid in ordered_ids():
        r3 = round3_stats_for(sid, r3_data)
        r4s = r4[sid]
        d_median = round(r4s["median"] - r3["median"], 4)
        d_iqr = round(r4s["iqr"] - r3["iqr"], 4)
        stable = abs(d_median) < STABILITY_MEDIAN_MAX and abs(d_iqr) < STABILITY_IQR_MAX
        rows[sid] = {
            "statement_id": sid,
            "section": R4_STATEMENTS[sid]["section"],
            "short_label": R4_STATEMENTS[sid]["short_label"],
            "r3_source_ids": r3["source_ids"],
            "r3_n": r3["n"], "r3_median": r3["median"], "r3_iqr": r3["iqr"],
            "r3_class": r3["consensus_class"],
            "r4_n": r4s["n_rated"], "r4_median": r4s["median"], "r4_iqr": r4s["iqr"],
            "r4_class": r4s["consensus_class"],
            "delta_median": d_median, "delta_iqr": d_iqr,
            "stable": stable,
            "movement": movement(r3["consensus_class"], r4s["consensus_class"]),
            "stable_non_consensus": r3["consensus_class"] == "non-consensus"
                                    and r4s["consensus_class"] == "non-consensus",
        }

    stable_non = [sid for sid, r in rows.items() if r["stable_non_consensus"]]
    moved_toward = [sid for sid, r in rows.items() if r["movement"] == "toward consensus"]
    moved_away = [sid for sid, r in rows.items() if r["movement"] == "away from consensus"]
    n_stable = sum(1 for r in rows.values() if r["stable"])

    return {
        "metadata": {
            "stability_rule": f"stable if |delta median| < {STABILITY_MEDIAN_MAX} "
                              f"and |delta IQR| < {STABILITY_IQR_MAX}",
            "n_statements": len(rows),
            "n_stable": n_stable,
        },
        "stable_non_consensus": stable_non,
        "moved_toward_consensus": moved_toward,
        "moved_away_from_consensus": moved_away,
        "statements": rows,
    }


def write_outputs(result: dict, output_dir: Path = None):
    output_dir = output_dir or ROUND4_ANALYSIS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "round3_vs_round4.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    csv_path = output_dir / "round3_vs_round4.csv"
    fields = ["statement_id", "section", "r3_source_ids", "r3_n", "r3_median", "r3_iqr",
              "r3_class", "r4_n", "r4_median", "r4_iqr", "r4_class", "delta_median",
              "delta_iqr", "stable", "movement", "short_label"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in ordered_ids():
            row = dict(result["statements"][sid])
            row["r3_source_ids"] = ", ".join(row["r3_source_ids"])
            w.writerow({k: row.get(k) for k in fields})
    return json_path, csv_path


def main(extracted_file: Path = None, output_dir: Path = None):
    result = compare(extracted_file)
    json_path, csv_path = write_outputs(result, output_dir)

    print("Crosswalk (Round 3 -> Round 4) for sign-off:")
    print(f"  {'R4':4} {'<- R3':10} {'R3 med(IQR)':>12} {'R4 med(IQR)':>12} {'move':>20} stable")
    for sid in ordered_ids():
        r = result["statements"][sid]
        print(f"  {sid:4} {', '.join(r['r3_source_ids']):10} "
              f"{r['r3_median']:>6}({r['r3_iqr']:<4}) {r['r4_median']:>6}({r['r4_iqr']:<4}) "
              f"{r['movement']:>20} {'yes' if r['stable'] else 'NO'}")
    print(f"\n[OK] Comparison -> {json_path}")
    print(f"     stable: {result['metadata']['n_stable']}/{result['metadata']['n_statements']}; "
          f"toward consensus: {len(result['moved_toward_consensus'])}; "
          f"away: {len(result['moved_away_from_consensus'])}; "
          f"stable non-consensus: {len(result['stable_non_consensus'])} "
          f"{result['stable_non_consensus']}")
    return result


if __name__ == "__main__":
    main()
