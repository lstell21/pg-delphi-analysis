"""
Round 4 stage 0: assemble the analysis dataset from the raw LimeSurvey export.

One panelist's final-round submission was split across several partial
attempts left by a technical interruption (response IDs 41, 45, 48 in the raw
export). These were reconstructed into a single response -- see
``round4_merged_record.csv`` and the Methods -- which also carries
that panelist's Section E ranking, collected out of band after the interruption
and therefore not recoverable from the export alone. This script applies the
consolidation deterministically: it drops the superseded fragment rows from the
raw export and appends the merged record, writing the dataset the rest of the
pipeline reads (``ROUND4_CSV``).

Re-running this on the two shared inputs reproduces the analysis dataset, so
every downstream statistic, table, and figure can be regenerated from the
publicly shared data:

    python scripts/r4_build_dataset.py
    python scripts/run_round4_pipeline.py

Inputs (both shared with the anonymized data):
  - round4_raw_export.csv            unmodified LimeSurvey full export
  - round4_merged_record.csv    reconstructed panelist's response (A--E)
Output:
  - round4_dataset.csv (= ROUND4_CSV)   analysis dataset
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import ROUND4_RAW_EXPORT, ROUND4_MERGED_RECORD, ROUND4_CSV

RAW_EXPORT = ROUND4_RAW_EXPORT
MERGED_RECORD = ROUND4_MERGED_RECORD

# Raw response IDs superseded by the reconstructed merged record; dropped to
# avoid double-counting the same panelist (see Methods, "Consensus definition").
SUPERSEDED_RESPONSE_IDS = {"41", "45", "48"}

# Partial re-attempts that a panelist abandoned before submitting a complete
# response. Each was identified by an exact match on all demographic fields plus
# a closely matching start time, and confirmed against the completed response's
# overlapping ratings. They are dropped so the panelist is counted once (the
# complete response is kept):
#   13, 17  -> completed as response 18 (all three started the same day, hours apart)
#   37      -> completed as response 47 (Section A ratings identical)
DUPLICATE_ATTEMPT_IDS = {"13", "17", "37"}

DROP_IDS = SUPERSEDED_RESPONSE_IDS | DUPLICATE_ATTEMPT_IDS


def build(raw_export: Path = RAW_EXPORT, merged: Path = MERGED_RECORD,
          output: Path = ROUND4_CSV) -> Path:
    if not raw_export.exists():
        raise FileNotFoundError(
            f"Raw export not found at {raw_export}. The analysis dataset cannot be "
            f"rebuilt without it; if it is already assembled at {output}, skip this step."
        )
    with open(raw_export, encoding="utf-8-sig", newline="") as f:
        raw = list(csv.reader(f))
    with open(merged, encoding="utf-8-sig", newline="") as f:
        mrg = list(csv.reader(f))

    header, rows = raw[0], raw[1:]
    if mrg[0] != header:
        raise ValueError("Merged record header does not match the raw export schema.")

    kept = [r for r in rows if r[0] not in DROP_IDS]
    n_dropped = len(rows) - len(kept)
    kept.append(mrg[1])

    with open(output, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(header)
        w.writerows(kept)

    print(f"[OK] Analysis dataset -> {output}")
    print(f"     raw rows {len(rows)}; dropped {n_dropped} row(s) "
          f"[superseded fragments {sorted(SUPERSEDED_RESPONSE_IDS)}, "
          f"duplicate attempts {sorted(DUPLICATE_ATTEMPT_IDS)}]; "
          f"+1 merged record; total {len(kept)}")
    return output


if __name__ == "__main__":
    build()
