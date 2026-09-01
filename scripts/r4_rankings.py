"""
Round 4 stage 5: Section E ranking aggregation.

Section E asked panelists to rank 7 preparedness priorities for three phases:
  E01 - before an epidemic/pandemic emerges
  E02 - during the early stage of emergence
  E03 - after the event, preparing for future pandemics

For each phase and item this reports the first-choice count, mean rank (lower =
more preferred), and Borda score (rank 1 -> 7 points ... rank 7 -> 1 point),
and orders the items by mean rank.

Outputs data/analysis/round-4/rankings.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from config import ROUND4_RESPONSES, ROUND4_ANALYSIS_DIR
from r4_statements import E_ITEMS, E_PHASES

N_ITEMS = len(E_ITEMS)  # 7


def aggregate_phase(submissions: list, phase: str) -> dict:
    """Aggregate one phase's rankings across submissions."""
    first_choice = {i: 0 for i in E_ITEMS}
    rank_lists = {i: [] for i in E_ITEMS}
    n_respondents = 0

    for sub in submissions:
        ordered = sub.get("rankings", {}).get(phase, [])
        if not ordered or all(v is None for v in ordered):
            continue
        n_respondents += 1
        for rank_index, item in enumerate(ordered):
            if item is None:
                continue
            rank = rank_index + 1  # 1-based
            rank_lists[item].append(rank)
            if rank == 1:
                first_choice[item] += 1

    items = []
    for item, text in E_ITEMS.items():
        ranks = np.array(rank_lists[item], dtype=float)
        mean_rank = round(float(np.mean(ranks)), 3) if len(ranks) else None
        # Borda: rank r -> (N_ITEMS + 1 - r) points.
        borda = int(np.sum(N_ITEMS + 1 - ranks)) if len(ranks) else 0
        items.append({
            "item_id": item,
            "text": text,
            "first_choice": first_choice[item],
            "n_ranked": len(ranks),
            "mean_rank": mean_rank,
            "borda": borda,
        })

    # Order by mean rank (ascending); items never ranked go last.
    items.sort(key=lambda x: (x["mean_rank"] is None, x["mean_rank"] if x["mean_rank"] is not None else 99))
    for pos, it in enumerate(items, 1):
        it["order"] = pos

    return {"description": E_PHASES[phase], "n_respondents": n_respondents, "items": items}


def compute_rankings(extracted_file: Path = None) -> dict:
    extracted_file = extracted_file or ROUND4_RESPONSES
    with open(extracted_file, encoding="utf-8") as f:
        data = json.load(f)
    submissions = data["submissions"]

    phases = {phase: aggregate_phase(submissions, phase) for phase in E_PHASES}
    return {
        "metadata": {
            "round": 4,
            "n_items": N_ITEMS,
            "scoring": "mean rank (lower=preferred); Borda: rank r -> (8-r) points; "
                       "first_choice = count ranked #1",
            "items": E_ITEMS,
        },
        "phases": phases,
    }


def main(extracted_file: Path = None, output_dir: Path = None):
    result = compute_rankings(extracted_file)
    output_dir = output_dir or ROUND4_ANALYSIS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "rankings.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[OK] Section E rankings -> {out}")
    for phase, pdata in result["phases"].items():
        print(f"\n  {phase}: {pdata['description']} (n={pdata['n_respondents']})")
        for it in pdata["items"][:3]:
            print(f"    {it['order']}. [{it['item_id']}] mean rank {it['mean_rank']}, "
                  f"first-choice {it['first_choice']} - {it['text'][:55]}")
    return result


if __name__ == "__main__":
    main()
