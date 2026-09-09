"""
Round 4 stage 2b: percentage endorsement and a completers-only sensitivity
analysis.

Two questions referees are likely to raise about a Delphi in which 38 of 40
statements reach the scale maximum:

  1. How much of the panel actually chose the top of the scale? Median and IQR
     saturate once agreement is high, so this module adds the share of raters
     choosing 5 or 6 ("endorsement"), which still discriminates between
     statements where the median and IQR no longer do.

  2. Does the result depend on partial responses? We retained partial responses
     for the statements a panellist rated, so per-statement denominators run
     from 43 to 51 while the reported panel size is the 41 who completed the
     round. This module recomputes every statistic on completers only and
     reports which statements change median, IQR, or consensus class.

Quartiles use linear interpolation (numpy's default, equivalent to R quantile
type 7), matching r4_consensus_stats.py.

Outputs data/generated/sensitivity.json and sensitivity.csv, and
tables/sensitivity.tex (Supplementary Table 5).
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
from r4_statements import R4_STATEMENTS, ordered_ids


def classify_consensus(iqr: float) -> str:
    if iqr <= CONSENSUS_IQR_MAX:
        return "consensus"
    if iqr <= NEAR_CONSENSUS_IQR_MAX:
        return "near-consensus"
    return "non-consensus"


def summarize(ratings: list) -> dict:
    """Median, IQR, endorsement and consensus class for one set of ratings."""
    arr = np.array(ratings, dtype=float)
    n = len(arr)
    if not n:
        return {"n_rated": 0, "median": None, "iqr": None,
                "pct_top2": None, "consensus_class": "no-data"}
    q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
    iqr = round(q3 - q1, 4)
    return {
        "n_rated": n,
        "median": float(np.median(arr)),
        "iqr": iqr,
        # share choosing 5 or 6, the two top points of the six-point scale
        "pct_top2": round(100.0 * float(np.mean(arr >= 5)), 1),
        "consensus_class": classify_consensus(iqr),
    }


def gather(submissions: list) -> dict:
    """Per-statement ratings, abstentions removed."""
    out = {sid: [] for sid in R4_STATEMENTS}
    for sub in submissions:
        for fb in sub["feedback"]:
            if fb.get("not_qualified"):
                continue
            if fb.get("rating") is not None:
                out[fb["statement_id"]].append(int(fb["rating"]))
    return out


def compute(extracted_file: Path = None) -> dict:
    extracted_file = extracted_file or ROUND4_RESPONSES
    with open(extracted_file, encoding="utf-8") as f:
        data = json.load(f)

    submissions = data["submissions"]
    completers = [s for s in submissions if s.get("complete")]

    all_ratings = gather(submissions)
    comp_ratings = gather(completers)

    statements, median_changes, class_changes = {}, [], []
    for sid in ordered_ids():
        a, c = summarize(all_ratings[sid]), summarize(comp_ratings[sid])
        if a["median"] != c["median"]:
            median_changes.append(sid)
        if a["consensus_class"] != c["consensus_class"]:
            class_changes.append(sid)
        statements[sid] = {"statement_id": sid, "all_raters": a, "completers_only": c}

    tops = [statements[s]["all_raters"]["pct_top2"] for s in statements]
    return {
        "metadata": {
            "round": 4,
            "n_submissions": len(submissions),
            "n_completers": len(completers),
            "quartile_method": "linear interpolation (numpy default, R quantile type 7)",
            "endorsement_definition": "share of raters choosing 5 or 6",
        },
        "overall": {
            "median_changes": median_changes,
            "consensus_class_changes": class_changes,
            "pct_top2_min": min(tops),
            "pct_top2_max": max(tops),
            "pct_top2_mean": round(sum(tops) / len(tops), 1),
            "n_median_6_all": sum(1 for s in statements
                                  if statements[s]["all_raters"]["median"] == 6),
            "n_median_6_completers": sum(1 for s in statements
                                         if statements[s]["completers_only"]["median"] == 6),
        },
        "statements": statements,
    }


def write_outputs(result: dict) -> None:
    ROUND4_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ROUND4_ANALYSIS_DIR / "sensitivity.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    with open(ROUND4_ANALYSIS_DIR / "sensitivity.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["statement_id",
                    "n_all", "median_all", "iqr_all", "pct_top2_all", "class_all",
                    "n_comp", "median_comp", "iqr_comp", "pct_top2_comp", "class_comp"])
        for sid, row in result["statements"].items():
            a, c = row["all_raters"], row["completers_only"]
            w.writerow([sid,
                        a["n_rated"], a["median"], a["iqr"], a["pct_top2"], a["consensus_class"],
                        c["n_rated"], c["median"], c["iqr"], c["pct_top2"], c["consensus_class"]])


SECTION_TITLES = {
    "A": "Model design and complexity",
    "B": "Data availability and quality",
    "C": "Uncertainty, validation, and communication",
    "D": "Collaboration, interdisciplinarity, and ethics",
}

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"


def num(x) -> str:
    """Drop the trailing .0 so 6.0 prints as 6 and 5.5 stays 5.5."""
    if x is None:
        return "--"
    return ("%g" % x)


def build_table(result: dict) -> str:
    changed = set(result["overall"]["median_changes"])
    rows = []
    for section in "ABCD":
        ids = [s for s in result["statements"] if s.startswith(section)]
        if not ids:
            continue
        rows.append(r"\multicolumn{9}{@{}l}{\textbf{Section %s: %s}}\\"
                    % (section, SECTION_TITLES[section]))
        rows.append(r"\addlinespace[2pt]")
        for sid in sorted(ids):
            a = result["statements"][sid]["all_raters"]
            c = result["statements"][sid]["completers_only"]
            mark = r"$^{*}$" if sid in changed else ""
            rows.append(r"%s%s & %s & %s & %.1f & %d & %s & %s & %.1f & %d \\"
                        % (sid, mark,
                           num(a["median"]), num(a["iqr"]), a["pct_top2"], a["n_rated"],
                           num(c["median"]), num(c["iqr"]), c["pct_top2"], c["n_rated"]))
        rows.append(r"\addlinespace[4pt]")
    body = "\n".join(rows).rstrip()
    # Same name as the main table's column, stacked over two lines so that
    # spelling it out costs no more width than "% 5--6" did.
    top2 = r"\begin{tabular}[b]{@{}c@{}}Top-two\\share (\%)\end{tabular}"
    header = (r"ID & Median & IQR & " + top2 + r" & $n$ & Median & IQR & "
              + top2 + r" & $n$ \\"
              "\n"
              r"\cmidrule(r){2-5}\cmidrule(l){6-9}")
    n_comp = result["metadata"]["n_completers"]
    return r"""%% Auto-generated by scripts/r4_sensitivity.py -- do not edit by hand.
\begingroup\footnotesize
\begin{longtable}{@{}l c c c c c c c c@{}}
\caption{\textbf{Completers-only sensitivity analysis and the top-two share.} Round~4
statistics on all raters, as reported in the main text, beside the same
statistics restricted to the %d panellists who completed the round. Quartiles use
linear interpolation; the top-two share is the percentage of raters choosing 5 or 6,
which ranges from %.0f\%% to %.0f\%% and still separates statements where median
and IQR no longer do. Shares are given to one decimal here and to the nearest
whole number in Table~1, so B08 reads 93.5 in this table and 93 there; both are
43 of 46. No statement changes consensus class, and one median moves
($^{*}$ A10, 5.5 to 5).}
\label{tab:sensitivity}\\
\toprule
& \multicolumn{4}{c}{All raters} & \multicolumn{4}{c}{Completers only} \\
%s
\endfirsthead
\caption[]{\emph{(continued)}}\\
\toprule
& \multicolumn{4}{c}{All raters} & \multicolumn{4}{c}{Completers only} \\
%s
\endhead
\midrule \multicolumn{9}{r}{\emph{continued on next page}}\\
\endfoot
\bottomrule
\endlastfoot
%s
\end{longtable}
\endgroup
""" % (n_comp, result["overall"]["pct_top2_min"], result["overall"]["pct_top2_max"],
       header, header, body)


def main() -> None:
    result = compute()
    write_outputs(result)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "sensitivity.tex").write_text(build_table(result), encoding="utf-8")
    print("wrote %s" % (TABLES_DIR / "sensitivity.tex"))
    m, o = result["metadata"], result["overall"]
    print("submissions %d, completers %d" % (m["n_submissions"], m["n_completers"]))
    print("endorsement (%% choosing 5 or 6): min %.1f, max %.1f, mean %.1f"
          % (o["pct_top2_min"], o["pct_top2_max"], o["pct_top2_mean"]))
    print("median 6: %d of 40 all raters, %d of 40 completers only"
          % (o["n_median_6_all"], o["n_median_6_completers"]))
    print("median changes on completers only : %s" % (o["median_changes"] or "none"))
    print("consensus class changes           : %s" % (o["consensus_class_changes"] or "none"))
    print("wrote %s" % (ROUND4_ANALYSIS_DIR / "sensitivity.json"))


if __name__ == "__main__":
    main()
