#!/usr/bin/env python3
"""
Round 4 agreement by statement origin, for the Discussion.

Each of the 40 consensus statements reached the final round by one of three
routes, recorded in the "origin" column of the provenance chain that
statement_provenance.py writes: it descends from the agent's first draft
("v1 draft"), or it was added in response to panel feedback ("added in Round 2",
"added in Round 3"). The Discussion asks whether the draft's statements drew
different agreement from those the panel added.

For two groups, the draft's statements ("v1 draft") and the panel-added ones
(both "added in" origins together), and for each of the three origins, it
counts the statements, those with an IQR of 0, and those at the highest median
(6), and gives the mean IQR. The ratings come from the Round 4 consensus
statistics that r4_consensus_stats.py writes. Both inputs are read with the csv
module only.

Usage:
    python scripts/statement_origin_agreement.py           # writes OUTPUT_CSV
    python scripts/statement_origin_agreement.py --check   # compares with it; writes nothing
"""
import argparse
import csv
import io
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROVENANCE_CSV = PROJECT_ROOT / "data" / "generated" / "provenance" / "provenance_chain.csv"
CONSENSUS_CSV = PROJECT_ROOT / "data" / "generated" / "consensus_stats.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "generated" / "origin_agreement.csv"

DRAFT = "v1 draft"
ADDED = ("added in Round 2", "added in Round 3")
GROUPS = {DRAFT: (DRAFT,), "panel-added": ADDED}
COLUMNS = ["level", "name", "n", "iqr_0", "median_6", "mean_iqr"]
TOP = 6.0   # the highest point of the six-point scale


def read_csv(path: Path) -> list:
    if not path.exists():
        raise SystemExit(f"error: {path} not found")
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def statements() -> dict:
    """{statement: (origin, IQR, median)} for the 40 final statements."""
    origin = {r["r4"]: r["origin"] for r in read_csv(PROVENANCE_CSV)}
    stats = {r["statement_id"]: (float(r["iqr"]), float(r["median"]))
             for r in read_csv(CONSENSUS_CSV)}
    if set(origin) != set(stats):
        raise SystemExit(f"error: the two inputs list different statements: only in the "
                         f"provenance chain {sorted(set(origin) - set(stats))}, only in the "
                         f"consensus statistics {sorted(set(stats) - set(origin))}")
    unknown = sorted({o for o in origin.values() if o != DRAFT and o not in ADDED})
    if unknown:
        raise SystemExit(f"error: unknown origin {unknown} in {PROVENANCE_CSV.name}")
    return {s: (origin[s], *stats[s]) for s in sorted(origin)}


def summary(level: str, name: str, rows: list) -> dict:
    iqrs = [iqr for _, iqr, _ in rows]
    return {"level": level, "name": name, "n": len(rows),
            "iqr_0": sum(1 for iqr in iqrs if iqr == 0),
            "median_6": sum(1 for _, _, median in rows if median == TOP),
            "mean_iqr": f"{sum(iqrs) / len(iqrs):.3f}" if rows else ""}


def table(data: dict) -> list:
    out = [summary("group", name, [v for v in data.values() if v[0] in origins])
           for name, origins in GROUPS.items()]
    out += [summary("origin", o, [v for v in data.values() if v[0] == o]) for o in (DRAFT, *ADDED)]
    return out


def as_csv(rows: list) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help=f"compare with {OUTPUT_CSV.name} and write nothing")
    args = ap.parse_args()

    rows = table(statements())
    for r in rows:
        print(f"  {r['level']:6s} {r['name']:17s} n = {r['n']:2d}, IQR 0: {r['iqr_0']:2d}, "
              f"median 6: {r['median_6']:2d}, mean IQR {r['mean_iqr']}")
    text = as_csv(rows)
    if args.check:
        if not OUTPUT_CSV.exists():
            print(f"FAIL: {OUTPUT_CSV} does not exist; run without --check")
            return 1
        if OUTPUT_CSV.read_text(encoding="utf-8") != text:
            print(f"FAIL: {OUTPUT_CSV} is stale; run without --check")
            return 1
        print(f"OK: {OUTPUT_CSV} is current")
        return 0
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print(f"wrote {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
