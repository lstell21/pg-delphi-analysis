#!/usr/bin/env python3
"""Audit a raw Round 4 survey export before anonymizing it.

Run this on the machine holding the LimeSurvey export. It prints every column
with its fill rate, cardinality, and a truncated sample value, and flags the ones
that are likely to identify a panelist. It changes nothing. The output is the
worksheet from which you build the drop list, so that the anonymization decision
is recorded against the real columns rather than assumed.

Three kinds of flag:

  DIRECT    names, emails, IP addresses, tokens. These always go.
  TIMING    timestamps and per-page durations. These reconstruct who submitted
            when, and the dataset build already matches attempts on overlapping
            start times, so they are a live re-identification route.
  QUASI     demographics and free text. Rare combinations single people out. The
            panel is named in the author list, so a country plus a role plus a
            career stage can be enough.

Usage:
    python scripts/audit_round4_export.py "R4/DELPHI analysis/survey_783452_raw_export.csv"
    python scripts/audit_round4_export.py <export.csv> --values country role
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

csv.field_size_limit(10_000_000)

NAME_RULES = [
    ("DIRECT", re.compile(r"(name|email|mail|ip[_ ]?addr|ipaddr|token|refurl|"
                          r"invit|participant|respondent|contact|affiliat|"
                          r"institut|orcid)", re.I)),
    ("TIMING", re.compile(r"(date|time|stamp|start|submit|last[_ ]?action|"
                          r"interview|duration|seconds)", re.I)),
    # \b around age and sex, or "pages" and "language" flag themselves
    ("QUASI", re.compile(r"(country|nation|region|gender|\bsex\b|\bage\b|career|"
                         r"experience|years|discipline|role|position|sector|"
                         r"seniority|degree|comment|other|specify|text|free)", re.I)),
]

VALUE_RULES = [
    ("DIRECT", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "looks like an email address"),
    ("DIRECT", re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "looks like an IP address"),
    ("TIMING", re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}"), "looks like a timestamp"),
]

RATING = re.compile(r"^[1-6](\.0)?$")


def classify(col: str, values: list) -> tuple:
    filled = [v for v in values if v.strip()]
    for level, rx in NAME_RULES:
        if rx.search(col):
            return level, f"column name matches /{rx.pattern[:28]}.../"
    for level, rx, why in VALUE_RULES:
        if sum(1 for v in filled[:200] if rx.search(v)) > len(filled[:200]) * 0.5:
            return level, why
    if filled and all(RATING.match(v.strip()) for v in filled):
        return "", "rating scale 1-6, keep"
    longest = max((len(v) for v in filled), default=0)
    if longest > 120:
        return "QUASI", f"free text, longest value {longest} chars"
    return "", ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", type=Path, help="raw survey export CSV")
    ap.add_argument("--values", nargs="*", default=[],
                    help="print the full value distribution for these columns")
    ap.add_argument("--delimiter", default=None, help="override the CSV delimiter")
    args = ap.parse_args()

    if not args.export.exists():
        sys.exit(f"error: {args.export} not found")

    with args.export.open(encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(64_000)
        fh.seek(0)
        delim = args.delimiter or csv.Sniffer().sniff(sample, ",;\t|").delimiter
        rows = list(csv.DictReader(fh, delimiter=delim))

    if not rows:
        sys.exit("error: no rows")
    cols = list(rows[0])
    print(f"{args.export.name}: {len(rows)} rows, {len(cols)} columns, "
          f"delimiter {delim!r}\n")

    header = f"{'flag':<7} {'column':<34} {'filled':>7} {'uniq':>6}  sample / why"
    print(header)
    print("-" * len(header))
    counts = Counter()
    for col in cols:
        values = [(r.get(col) or "") for r in rows]
        filled = [v for v in values if v.strip()]
        level, why = classify(col, values)
        counts[level or "keep"] += 1
        shown = why or (filled[0][:44].replace("\n", " ") if filled else "")
        print(f"{level:<7} {col[:34]:<34} {len(filled):>7} "
              f"{len(set(filled)):>6}  {shown}")

    print(f"\n{counts['DIRECT']} DIRECT, {counts['TIMING']} TIMING, "
          f"{counts['QUASI']} QUASI, {counts['keep']} unflagged.")
    print("\nDIRECT and TIMING columns should be dropped. Decide QUASI columns one\n"
          "by one: check the value distribution with --values <col> and drop or\n"
          "coarsen any category holding fewer than five panelists.")

    for col in args.values:
        if col not in cols:
            print(f"\n--values: no column {col!r}")
            continue
        dist = Counter((r.get(col) or "").strip() for r in rows)
        print(f"\n{col}:")
        for value, n in dist.most_common():
            mark = "  <-- fewer than 5" if 0 < n < 5 and value else ""
            print(f"    {n:>4}  {value[:60]!r}{mark}")


if __name__ == "__main__":
    main()
