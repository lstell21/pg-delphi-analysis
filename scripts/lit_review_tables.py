#!/usr/bin/env python3
"""
Literature review LaTeX tables.

Counterpart to r4_latex_tables.py (which covers the Round 4 Delphi data). This
one reads a screening run exported by pg-literature-screening and generates:

  * tables/study_characteristics.tex   -> tab:study_characteristics
      Publication period, publication type, and relevance band.
      Score distribution and mean for each relevance criterion.

Both are written to tables/, the only live manuscript tree, which must stay
byte-identical. \\input them from SI_B_results.tex in place of the hand-written
tables.

Only rows with Status "ok" and Decision "include" are counted. Columns are read
by header name, so added or reordered columns are harmless; a missing column, or
a Type outside PAPER_TYPES, is a hard error naming what was found.

Usage:
    python scripts/lit_review_tables.py --run path/to/full-run.csv
    python scripts/lit_review_tables.py --run ... --check-only
    python scripts/lit_review_tables.py --run ... --out-dir /tmp/preview
"""

import argparse
import collections
import csv
import re
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUT_DIRS = [
    PROJECT_ROOT / "tables",
]

# ── Data contract ─────────────────────────────────────────────────────────────
# Source of truth is pgscreen/rubric.py in the pg-literature-screening repo.
# Kept as a literal copy rather than an import, because that repo is a separate
# checkout. If the two drift, the validator below fails loudly with the offending
# values, which is the intended failure mode.

PAPER_TYPES = [
    "Research article", "Review article", "Systematic review", "Meta-analysis",
    "Perspective/Opinion", "Editorial", "Commentary", "Letter",
    "Conference paper", "Technical report", "Policy paper",
    "Book chapter", "Book", "Thesis", "Preprint", "Other",
]

COL_YEAR = "Publication Year"
COL_TYPE = "Type"
COL_DECISION = "Decision"
COL_MODEL_DECISION = "Model Decision"
COL_STATUS = "Status"
COL_MODEL = "Model"
COL_RUBRIC = "Rubric Version"

# (CSV column, printed label). Each scored 0-2; the overall score is their sum.
# Public health relevance and modeling relevance are NOT here: from rubric
# 2026-07-28.x they are eligibility gates (C3, C2 below), not scored dimensions.
# That is the fix for the old rubric's non-discrimination, where both sat at
# ~2.00 for every publication and inflated the overall score.
CRITERIA = [
    ("Score (Evidence Base)", "Evidence base"),
    ("Score (Breadth of Discussion)", "Breadth of discussion"),
    ("Score (Acknowledgment of Uncertainty & Bias)", "Uncertainty and bias"),
    ("Score (Transparency)", "Transparency"),
]
MAX_SCORE = 2 * len(CRITERIA)

# Eligibility gates, each "met" or "not met". Reported for the screening
# narrative, not scored.
ELIGIBILITY = [
    ("C1 Scope", "Scope"),
    ("C2 Model-Based Approach", "Model-based approach"),
    ("C3 Public Health Relevance", "Public health relevance"),
    ("C4 Challenges", "Critical discussion of challenges"),
    ("C5 Broader Perspective", "Broader perspective"),
]

COL_DISEASE = "Specific Disease(s)"

# ── Disease focus ─────────────────────────────────────────────────────────────
# "Specific Disease(s)" is free text, so it is mapped onto the categories the
# manuscript has always used. Matching is by disease *family*, not by splitting
# the string: "SARS-CoV-2/COVID-19" and "AIDS/HIV" use the slash for synonyms,
# so a naive split would call them two diseases. A record counts as multiple
# only when two distinct families appear, or the text says so outright.
#
# Anything non-empty that matches no family lands in "Other", and every value
# routed to Other or Multiple is echoed to the console for eyeballing. Extend the
# patterns rather than letting a misread sit in Other.

DISEASE_FAMILIES = [
    ("COVID-19", [r"covid", r"sars[\s\-]?cov[\s\-]?2"]),   # not bare "sars" (2003 SARS)
    ("Influenza", [r"influenza", r"\bflu\b", r"h1n1", r"h3n2", r"h5n1", r"h7n9"]),
    ("HIV/AIDS", [r"\bhiv\b", r"\baids\b"]),
    ("Ebola", [r"ebola", r"\bevd\b"]),
]

NON_SPECIFIC = {"", "na", "n/a", "none", "-", "--", "not specified", "not specific",
                "nonspecific", "non-specific", "general", "generic", "any",
                "not applicable", "unspecified"}

MULTI_MARKERS = [r"\bmultiple\b", r"\bvarious\b", r"\bseveral\b", r"\brange of\b",
                 r"\bmany\b", r"\bdiverse\b"]

# The column records a *primary* focus, but entries often append illustrative or
# comparative mentions ("COVID-19, with comparative reference to H1N1"). Those
# must not turn one disease into "multiple", so the text is cut at the first
# such marker before any matching.
SECONDARY_MARKERS = [
    r",?\s*\bincluding\b", r",?\s*\bwith comparative reference\b",
    r",?\s*\bwith generalization\b", r",?\s*\bwith reference\b",
    r",?\s*\bsuch as\b", r",?\s*\be\.g\.", r",?\s*\bfor example\b",
    r",?\s*\billustrative\b", r",?\s*\bimplied as\b", r",?\s*\bas examples\b",
    r"\s+and its\b", r"\s+and their\b",
]

# A segment that is only a generic category ("respiratory viruses", "other
# pathogens") names no second disease, so it must not tip a record into
# "multiple". Specific names ending in the same nouns ("hepatitis C virus") do
# not match, because the prefix list is closed.
GENERIC_SEGMENT = re.compile(
    r"(other\s+|emerging\s+|human\s+)?"
    r"(respiratory\s+|infectious\s+|viral\s+|bacterial\s+|zoonotic\s+)?"
    r"(virus(es)?|pathogens?|diseases?|infections?|outbreaks?|illnesses?|conditions?)$"
)

CAT_MULTIPLE = "Multiple diseases"
CAT_NONSPECIFIC = "Non-specific/general"
CAT_OTHER = "Other"

PERIOD_BINS = [
    ("Before 2010", None, 2009),
    ("2010 to 2014", 2010, 2014),
    ("2015 to 2019", 2015, 2019),
    ("2020 to 2021", 2020, 2021),
    ("2022 onward", 2022, None),
]

# Bands for the 0-8 scale (four criteria, 0-2 each). High means at most one
# criterion short of full marks. On the 2026-07-28 full run these split
# 68/30/2, which is the discrimination the old 0-12 rubric lacked (96% high).
# Boundaries are a manuscript decision, not a pipeline one: change them here.
RELEVANCE_BANDS = [
    ("High (7 to 8)", 7, 8),
    ("Moderate (5 to 6)", 5, 6),
    ("Low (below 5)", 0, 4),
]


def tex_escape(s: str) -> str:
    repl = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def classify_disease(raw: str) -> str:
    """Map a free-text Specific Disease(s) value onto a manuscript category."""
    text = (raw or "").strip()
    if text.lower() in NON_SPECIFIC:
        return CAT_NONSPECIFIC

    # Parenthetical asides and trailing secondary mentions are commentary on the
    # primary focus, not additional focuses, so drop both before matching.
    low = re.sub(r"\([^)]*\)", " ", text.lower())
    for marker in SECONDARY_MARKERS:
        low = re.split(marker, low, maxsplit=1)[0]
    low = low.strip(" ,;")

    families = {name for name, pats in DISEASE_FAMILIES
                if any(re.search(p, low) for p in pats)}

    if any(re.search(m, low) for m in MULTI_MARKERS):
        return CAT_MULTIPLE
    if len(families) >= 2:
        return CAT_MULTIPLE

    # A comma/"and" list can pair a known family with a disease we do not track
    # ("HIV and tuberculosis"), which the family count alone misses. Count
    # distinct diseases across the segments instead. Parenthetical asides are
    # stripped first, because they routinely carry commas ("Influenza (pandemic
    # influenza, H5N1)") without naming a second disease. A slash is left alone:
    # it means synonym here ("SARS-CoV-2/COVID-19"), not list.
    segments = [s.strip() for s in re.split(r"[;,]|\band\b", low) if s.strip()]
    if len(segments) >= 2:
        seg_families, unknown = set(), 0
        for seg in segments:
            hit = {name for name, pats in DISEASE_FAMILIES
                   if any(re.search(p, seg) for p in pats)}
            if hit:
                seg_families |= hit
            elif (len(seg) >= 3
                    and not re.match(r"(its|their|which|that|the)\b", seg)
                    and not GENERIC_SEGMENT.fullmatch(seg)):
                unknown += 1             # a disease name, not a continuation
        if len(seg_families) + unknown >= 2:
            return CAT_MULTIPLE

    if len(families) == 1:
        return next(iter(families))
    return CAT_OTHER


def as_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def read_run(path: Path):
    """Return (included_records, meta). Rows are filtered to Status ok / included."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fields = reader.fieldnames or []

    required = [COL_YEAR, COL_TYPE, COL_DECISION, COL_STATUS] + [c for c, _ in CRITERIA]
    missing = [c for c in required if c not in fields]
    if missing:
        raise SystemExit("error: missing columns: " + ", ".join(missing) +
                         "\n       found: " + ", ".join(fields))

    kept, skipped = [], collections.Counter()
    for i, row in enumerate(rows, start=2):          # 1 is the header
        status = (row.get(COL_STATUS) or "").strip().lower()
        decision = (row.get(COL_DECISION) or "").strip().lower()
        if status != "ok":
            skipped[f"status={status or '(blank)'}"] += 1
            continue
        if decision != "include":
            skipped[f"decision={decision or '(blank)'}"] += 1
            continue
        scores = {label: as_int(row.get(col)) for col, label in CRITERIA}
        # Only sum when every criterion parsed; a partial row is an error, not a
        # low score. validate() reports which lines.
        present = [v for v in scores.values() if v is not None]
        kept.append({
            "line": i,
            "year": as_int(row.get(COL_YEAR)),
            "type": (row.get(COL_TYPE) or "").strip(),
            "disease_raw": (row.get(COL_DISEASE) or "").strip(),
            "disease": classify_disease(row.get(COL_DISEASE) or ""),
            "scores": scores,
            "overall": sum(present) if len(present) == len(CRITERIA) else None,
            "model_decision": (row.get(COL_MODEL_DECISION) or "").strip().lower(),
        })

    meta = {
        "total_rows": len(rows),
        "skipped": skipped,
        "models": sorted({(r.get(COL_MODEL) or "").strip() for r in rows} - {""}),
        "rubrics": sorted({(r.get(COL_RUBRIC) or "").strip() for r in rows} - {""}),
    }
    return kept, meta


def validate(recs) -> None:
    allowed = set(PAPER_TYPES)
    bad = collections.defaultdict(list)
    for r in recs:
        if r["type"] not in allowed:
            bad[r["type"] or "(blank)"].append(r["line"])
    if bad:
        print("error: publication types outside the controlled vocabulary:", file=sys.stderr)
        for val, lines in sorted(bad.items(), key=lambda kv: -len(kv[1])):
            shown = ", ".join(str(x) for x in lines[:10])
            more = f" (+{len(lines) - 10} more)" if len(lines) > 10 else ""
            print(f"    {len(lines):4d}  {val!r}  CSV lines {shown}{more}", file=sys.stderr)
        print("\n  allowed (pgscreen/rubric.py PAPER_TYPES): " + ", ".join(PAPER_TYPES),
              file=sys.stderr)
        raise SystemExit(1)

    nulls = [r["line"] for r in recs if r["overall"] is None]
    if nulls:
        raise SystemExit(
            f"error: {len(nulls)} included row(s) have a non-numeric criterion score, "
            f"CSV lines {', '.join(str(x) for x in nulls[:10])}"
        )


def pct(c: int, n: int) -> str:
    return f"{100 * c / n:.1f}"


def disease_rows(recs):
    """(label, count) for the disease block: named diseases by frequency, then
    the three catch-alls, so the specific findings lead and zeros are dropped."""
    counts = collections.Counter(r["disease"] for r in recs)
    catch_all = [CAT_MULTIPLE, CAT_NONSPECIFIC, CAT_OTHER]
    named = sorted(((k, v) for k, v in counts.items() if k not in catch_all),
                   key=lambda kv: (-kv[1], kv[0]))
    tail = [(k, counts[k]) for k in catch_all if counts.get(k)]
    return named + tail


def build_characteristics(recs) -> str:
    n = len(recs)
    L = ["% Auto-generated by scripts/lit_review_tables.py -- do not edit by hand.",
         r"\begingroup\small",
         r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.76\textwidth} r r@{}}",
         rf"\caption{{\textbf{{Publication characteristics of the review corpus.}} Characteristics of the {n} included publications. Publication types follow "
         rf"a controlled vocabulary applied to every record, and types with no publications are "
         rf"omitted. Percentages are of the {n} publications and may not sum to 100 due to "
         rf"rounding.}}"
         r"\label{tab:study_characteristics}\\",
         r"\toprule",
         r"\textbf{Characteristic} & \textbf{$n$} & \textbf{\%} \\", r"\midrule",
         r"\endfirsthead",
         r"\caption[]{\emph{(continued)}}\\",
         r"\toprule",
         r"\textbf{Characteristic} & \textbf{$n$} & \textbf{\%} \\", r"\midrule",
         r"\endhead",
         r"\midrule \multicolumn{3}{r}{\emph{continued on next page}}\\",
         r"\endfoot",
         r"\bottomrule",
         r"\endlastfoot"]

    L.append(r"\multicolumn{3}{l}{\textit{Publication period}} \\")
    for label, lo, hi in PERIOD_BINS:
        c = sum(1 for r in recs if r["year"] is not None
                and (lo is None or r["year"] >= lo)
                and (hi is None or r["year"] <= hi))
        if c:
            L.append(rf"\quad {label} & {c} & {pct(c, n)} \\")

    L.append(r"\addlinespace")
    L.append(r"\multicolumn{3}{l}{\textit{Publication type}} \\")
    counts = collections.Counter(r["type"] for r in recs)
    for label in PAPER_TYPES:                    # canonical order, zeros dropped
        c = counts.get(label, 0)
        if c:
            L.append(rf"\quad {tex_escape(label)} & {c} & {pct(c, n)} \\")

    L.append(r"\addlinespace")
    L.append(r"\multicolumn{3}{l}{\textit{Primary disease focus}} \\")
    for label, c in disease_rows(recs):
        L.append(rf"\quad {tex_escape(label)} & {c} & {pct(c, n)} \\")

    L.append(r"\addlinespace")
    L.append(r"\multicolumn{3}{l}{\textit{Relevance band}} \\")
    for label, lo, hi in RELEVANCE_BANDS:
        c = sum(1 for r in recs if lo <= r["overall"] <= hi)
        if c:
            L.append(rf"\quad {label} & {c} & {pct(c, n)} \\")

    L += [r"\end{longtable}", r"\endgroup", ""]
    return "\n".join(L)


def build_criteria(recs) -> str:
    n = len(recs)
    L = ["% Auto-generated by scripts/lit_review_tables.py -- do not edit by hand.",
         r"\begin{table}[!htbp]", r"\centering",
         # Every segment containing a brace must be an f-string, or `}}` stays
         # two literal braces and breaks the caption.
         rf"\caption{{\textbf{{Relevance scores by criterion.}} Scores across the {n} included publications. Each "
         rf"criterion is scored 0 to 2, giving a maximum of {MAX_SCORE}. For each criterion, the "
         rf"number and percentage of publications receiving each score are reported, with the "
         rf"criterion mean.}}"
         r"\label{tab:quality_by_criterion}",
         r"\begingroup\small",
         r"\begin{tabularx}{\textwidth}{X r r r r}", r"\toprule",
         r"\textbf{Criterion} & \textbf{Score 0} & \textbf{Score 1} & \textbf{Score 2} & \textbf{Mean} \\",
         r"\midrule"]

    for _, label in CRITERIA:
        vals = [r["scores"][label] for r in recs]
        cells = [rf"{sum(1 for v in vals if v == s)} ({pct(sum(1 for v in vals if v == s), n)}\%)"
                 for s in (0, 1, 2)]
        L.append(rf"{tex_escape(label)} & " + " & ".join(cells) +
                 rf" & {statistics.mean(vals):.2f} \\")

    totals = [r["overall"] for r in recs]
    sd = statistics.stdev(totals) if len(totals) > 1 else 0.0
    L.append(r"\midrule")
    L.append(rf"\multicolumn{{4}}{{l}}{{Overall total score}} & "
             rf"{statistics.mean(totals):.1f} (SD {sd:.1f}) \\")
    L += [r"\bottomrule", r"\end{tabularx}", r"\endgroup", r"\end{table}", ""]
    return "\n".join(L)


def write(name: str, text: str, out_dirs=None) -> None:
    for d in (out_dirs or OUT_DIRS):
        d = Path(d)
        d.mkdir(parents=True, exist_ok=True)
        path = d / name
        # CRLF: the tree uses Windows line endings and the two tables/ copies
        # are compared byte-for-byte.
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        try:
            print(f"  wrote {path.relative_to(PROJECT_ROOT)}")
        except ValueError:
            print(f"  wrote {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True,
                    help="screening run CSV exported by pg-literature-screening")
    ap.add_argument("--check-only", action="store_true",
                    help="validate and print counts without writing files")
    ap.add_argument("--out-dir", type=Path, action="append",
                    help="write here instead of the manuscript trees (repeatable)")
    args = ap.parse_args()

    if not args.run.exists():
        raise SystemExit(f"error: run not found: {args.run}")

    recs, meta = read_run(args.run)
    print(f"  {args.run.name}: {meta['total_rows']} rows -> {len(recs)} included")
    if meta["skipped"]:
        print("    skipped: " + ", ".join(f"{v} {k}" for k, v in meta["skipped"].most_common()))
    if meta["models"]:
        print(f"    model: {', '.join(meta['models'])}   rubric: {', '.join(meta['rubrics'])}")
    print()

    if not recs:
        raise SystemExit("error: no included rows.")
    validate(recs)

    counts = collections.Counter(r["type"] for r in recs)
    for label in PAPER_TYPES:
        if counts.get(label):
            print(f"    {counts[label]:4d}  {pct(counts[label], len(recs)):>5}%  {label}")

    print()
    for label, c in disease_rows(recs):
        print(f"    {c:4d}  {pct(c, len(recs)):>5}%  {label}")

    # Disease focus is derived from free text, so show what the judgement calls
    # were built from. A misread here is silent otherwise.
    for cat in (CAT_OTHER, CAT_MULTIPLE):
        vals = sorted({r["disease_raw"] for r in recs if r["disease"] == cat})
        if vals:
            print(f"\n    raw values mapped to {cat!r} (check these):")
            for v in vals[:15]:
                print(f"      {v[:88]!r}")
            if len(vals) > 15:
                print(f"      ... and {len(vals) - 15} more")

    # Model-vs-recorded decision agreement, when both are present. Not a table,
    # but the number the Methods needs for the LLM validation claim.
    both = [r for r in recs if r["model_decision"]]
    if both:
        agree = sum(1 for r in both if r["model_decision"] == "include")
        print(f"\n    model/recorded decision agreement on included rows: "
              f"{agree}/{len(both)} ({100 * agree / len(both):.1f}%)")
    print()

    if args.check_only:
        print("  --check-only: no files written")
        return 0

    write("study_characteristics.tex", build_characteristics(recs), args.out_dir)
    # relevance_by_criterion.tex is no longer part of the manuscript; the builder
    # is kept so the table can still be regenerated.
    return 0


if __name__ == "__main__":
    sys.exit(main())
