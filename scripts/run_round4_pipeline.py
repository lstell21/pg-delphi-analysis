"""
Round 4 pipeline orchestrator.

Runs the Round 4 stages end to end. Every stage is deterministic: given the two
deposited raw files, this reproduces the reported statistics, tables, and
figures exactly, with no network access and no API key.

Prerequisite (run once): scripts/r4_build_dataset.py assembles the analysis
dataset (ROUND4_CSV) from the raw export plus the reconstructed record.

Stages:
  1. extract LimeSurvey CSV          -> data/generated/
  2. consensus statistics            -> data/generated/
  3. Round 3 vs Round 4 comparison   -> data/generated/   (reads R3 read-only)
  4. Section E rankings              -> data/generated/
  5. LaTeX tables + figure           -> tables/, figures/

Usage:
  python scripts/run_round4_pipeline.py
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

import r4_extract_from_csv
import r4_consensus_stats
import r4_round_comparison
import r4_rankings
import r4_latex_tables


def banner(n, title):
    print("\n" + "=" * 70)
    print(f"ROUND 4 - STAGE {n}: {title}")
    print("=" * 70)


def run():
    banner(1, "Extract LimeSurvey CSV")
    r4_extract_from_csv.extract()

    banner(2, "Consensus statistics")
    r4_consensus_stats.main()

    banner(3, "Round 3 vs Round 4 comparison")
    r4_round_comparison.main()

    banner(4, "Section E rankings")
    r4_rankings.main()

    banner(5, "LaTeX tables + figure")
    r4_latex_tables.main()

    print("\n" + "=" * 70)
    print("ROUND 4 PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run()
