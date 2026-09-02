"""Generate ``priorities.tex`` -- the ten actionable inter-pandemic priorities,
grouped by what each one demands and deliberately not ranked.

The priorities are an authorial synthesis: each groups several consensus
recommendations under one actionable heading. Both the grouping and the
headings are editorial and live in ``PRIORITY_GROUPS`` below.

Why there is no ordering
------------------------
An earlier version of this table ranked the ten by strength of consensus (mean
interquartile range of the supporting statements, ascending). That ordering was
withdrawn because it did not measure what a reader takes a numbered priority
list to mean. IQR measures dispersion among raters, so it says how homogeneous
agreement was, not how important or urgent the priority is. A statement can
command unanimous agreement and still matter little for preparedness, and a
genuinely urgent one can remain contested. The study never asked the panel to
rate the priorities on importance, so no defensible ranking key exists in these
data.

The panel did express importance directly, but in a separate instrument: the
Section E ranking task, in which panelists ranked seven preparedness measures
across three phases (see ``r4_statements.py``). Those seven do not map one to
one onto these ten, so the ranking task is reported in the caption and, in
full, in Supplementary Table 6 of Supplementary Note 7 rather than used to
order this table.

Priorities are therefore listed alphabetically within each group, and the
caption says so, so that no reader infers a hidden ranking from the order.

What this script still guarantees
---------------------------------
1. Every statement ID cited by a priority exists in the Round 4 ratings, so a
   renamed or dropped statement fails loudly instead of dangling.
2. The consensus metrics are still printed as diagnostics, so a large shift in
   the ratings is visible even though nothing depends on it for ordering.

Source of the ratings, in order of preference:

1. ``data/generated/consensus_stats.json`` -- the Round 4 analysis
   output, which is what r4_latex_tables.py builds the appendix table from.
   When this is present the generated table is cross-checked against it and a
   mismatch is a hard error, since a stale table would silently propagate.
2. ``tables//round4_consensus_table.tex`` -- the generated table, parsed
   back. Used when (1) is absent, which is the normal state of a fresh clone:
   ``data/`` is gitignored in this repo, so the Round 4 ratings are not in
   version control and exist only on the machine that ran the pipeline.

Because mode (2) cannot rule out stale data, it never proceeds quietly: the
run prints an UNVERIFIED banner, and **regenerating the table is refused**
unless --allow-unverified is passed. --check still works in that mode, since
verifying the committed artifacts against each other remains useful, but it
says plainly that the ratings themselves went unchecked.

Writes to tables/, the only live manuscript tree.

Run: python scripts/priorities_table.py
     python scripts/priorities_table.py --check              (verify, write nothing)
     python scripts/priorities_table.py --allow-unverified   (write without the source)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# The "must act" labels are Table 1's, imported rather than restated so the
# two tables cannot disagree about who has to act on a statement.
from main_text_tables import AUDIENCE  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIRS = [
    PROJECT_ROOT / "tables",
]
# Round 4 analysis output, the true source of the ratings. Not in version
# control (data/ is gitignored), so it is present only where the pipeline ran.
ROUND4_ANALYSIS_DIR = PROJECT_ROOT / "data" / "generated"

# ── The ten priorities, grouped ───────────────────────────────────────────────
# (group heading, [(priority heading, supporting statement IDs, topic)])
#
# The topic is a short descriptor of what the supporting statements are about.
# Four match a review theme exactly, two are shortened themes, and the rest are
# section names or descriptors with no theme equivalent, since the eight themes
# cover neither validation nor ethics. The column header says "topic" for that
# reason: calling it a review theme would be wrong for six of the ten rows.
#
# Editorial groupings, not panel-rated objects. Statement IDs must exist in
# round4_consensus_table.tex; the script fails loudly if one does not.
#
# Groups are emitted in the order given here, which follows the argument in the
# Results and carries no claim of relative importance. Priorities WITHIN a group
# are sorted alphabetically by the script, so do not hand-order them.
PRIORITY_GROUPS = [
    ("Data and infrastructure", [
        ("External model validation systems",
         ["C04"], "validation"),
        ("Interoperable real-time surveillance",
         ["B01", "C07", "C08", "D03"], "data governance and infrastructure"),
    ]),
    ("Modelling practice and methods", [
        ("Behavioural and social science integration",
         ["A10", "B04"], "model development and methodological improvement"),
        ("Model-selection guidance (fitness for purpose)",
         ["A01", "A04"], "model design and complexity"),
        ("Protocols for multi-model ensembles",
         ["A03", "C02"], "structural-uncertainty quantification"),
        ("Standardised uncertainty communication",
         ["C01", "C02", "C09", "C10"], "uncertainty quantification and communication"),
        ("Transparent, reproducible model reporting",
         ["A13", "B02", "C05"], "transparency and reproducibility"),
    ]),
    ("Governance, cooperation, and ethics", [
        ("Global cooperation and equity-sensitive models",
         ["D02", "D07", "D08", "B08"], "capacity building and global equity"),
        ("Pre-established science-policy structures",
         ["A12", "D01"], "science-policy interface"),
        ("Rapid ethical governance frameworks",
         ["D05", "D06", "B08"], "collaboration, interdisciplinarity, and ethics"),
    ]),
]

# ── What each priority asks for, in one sentence ─────────────────────────────
# Editorial summaries of the supporting statements, written so that a reader can
# work through the table without turning back to Table 1. Keyed by the priority
# name above; every priority must have one or the build fails.
GLOSS = {
    "External model validation systems":
        "Test performance on data not used for fitting, keep validation "
        "distinct from calibration, and update it as empirical data arrive.",
    "Interoperable real-time surveillance":
        "Timely data with documented limitations, released in machine-readable "
        "form through free, documented, versioned interfaces, and cross-border "
        "sharing agreements settled in advance.",
    "Behavioural and social science integration":
        "Justify socio-economic and behavioural detail against the question "
        "asked, and collect socio-behavioural data alongside clinical "
        "surveillance from the outset.",
    "Model-selection guidance (fitness for purpose)":
        "Judge a model against the question it addresses, and state the "
        "simplifying assumptions and boundary conditions a simple model rests "
        "on.",
    "Protocols for multi-model ensembles":
        "Combine structurally different models so that convergence signals "
        "robustness and divergence exposes structural uncertainty, then "
        "quantify that uncertainty by type.",
    "Standardised uncertainty communication":
        "Report uncertainty as ranges rather than point values, tie it to the "
        "decisions a model informs, and convey it to policymakers, the public, "
        "and the media alike.",
    "Transparent, reproducible model reporting":
        "Report calibration method, parameters, sources, and assumptions; "
        "share models, data, and code under the FAIR principles; and attach "
        "sensitivity analyses to every policy-informing output.",
    "Global cooperation and equity-sensitive models":
        "Joint modelling hubs and capacity building in under-resourced "
        "settings, age-stratified impacts on vulnerable groups, community "
        "advisory mechanisms, and ethical frameworks for data inequity.",
    "Pre-established science-policy structures":
        "Standing interdisciplinary collaborations, and models scoped to the "
        "decision context and the data actually available.",
    "Rapid ethical governance frameworks":
        "Embed ethics upstream in model development, validation, and "
        "communication, identify and mitigate bias, and agree safeguards "
        "before a pandemic rather than during one.",
}


def must_act(ids: list) -> str:
    """The parties that must act on a priority: the union over its statements."""
    parties = set()
    for i in ids:
        parties |= {x.strip() for x in AUDIENCE[i].split(",")}
    return ", ".join(x for x in ("M", "A", "P") if x in parties)


HEADER = r"""% Ten actionable priorities, grouped by what each demands and deliberately NOT
% ranked: the study measured agreement with the statements, and agreement is
% dispersion among raters, not importance. See the module docstring of
% scripts/priorities_table.py for why the earlier consensus-strength ordering
% was withdrawn. Auto-generated -- do not add numbering or reorder by hand;
% priorities are alphabetical within each group. Re-run that script after the
% Round 4 ratings change.
% Statement IDs refer to Table~\\ref{tab:recommendations_main}."""

CAPTION = (
    # Raw string: a plain "\textbf" would put a literal tab in the caption,
    # which pdflatex swallows silently and prints "extbf{...}".
    #
    # "Supplementary Table~6" is written out rather than \ref'd on purpose. The
    # Supplementary Information is a separate LaTeX document (SI_main.tex), so
    # its labels are not in this document's .aux and a \ref would typeset "??".
    # Every other cross-document pointer in the manuscript is spelled out the
    # same way. tab:rankings is Table 6: it is the sixth table environment in
    # SI_notes.tex, after tab:revision_mapping, which is Table 5. Renumber here
    # if a table is added or moved before it.
    r"\textbf{Ten priorities for the inter-pandemic period.} Priorities "
    "synthesised from the consensus recommendations and the review, grouped by "
    "what each demands and listed alphabetically within each group. The panel "
    "rated neither the priorities nor their relative importance, so no order "
    "here implies any: agreement is not importance, since a statement can "
    "command consensus yet matter little for preparedness. The panel did rank "
    "seven preparedness measures across three phases, and those do not "
    "correspond one to one with these ten (Supplementary Table~6). "
    "``Must act'' uses M, A, and P as in Table~\\ref{tab:recommendations_main}, "
    "and is the union of the parties named for the supporting statements. It "
    "is our judgement rather than the panel\'s. Every priority requires "
    "modelling groups to act, but only two of the ten can be delivered by a "
    "modelling group alone."
)


def read_stats_from_json(analysis_dir: Path) -> dict:
    """{id: (median, iqr, n)} from the Round 4 analysis output, the real source.

    Schema matches what r4_latex_tables.py consumes: consensus["statements"][id]
    with median, iqr, and n_rated.
    """
    with open(analysis_dir / "consensus_stats.json", encoding="utf-8") as f:
        consensus = json.load(f)
    return {sid: (float(cs["median"]), float(cs["iqr"]), int(cs["n_rated"]))
            for sid, cs in consensus["statements"].items()}


def read_stats_from_tex(tables_dir: Path) -> dict:
    """{id: (median, iqr, n)} parsed back out of the generated Round 4 table.

    Fallback for checkouts without the Round 4 analysis output (data/ is
    gitignored, so that is the normal state of a fresh clone). The table is
    itself generated from consensus_stats.json, so this reproduces the
    published figures but cannot detect a table that has gone stale relative
    to the ratings.
    """
    src = (tables_dir / "round4_consensus_table.tex").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
        r"^([ABCD]\d\d) & .*? & [\d.]+ \([\d.]+\) & ([\d.]+) \(([\d.]+)\) & (\d+) &",
        src, re.M,
    ):
        out[m.group(1)] = (float(m.group(2)), float(m.group(3)), int(m.group(4)))
    return out


def read_round4_stats() -> tuple:
    """Prefer the analysis JSON; fall back to the generated table.

    When both are available they must agree: a mismatch means
    round4_consensus_table.tex is stale and r4_latex_tables.py needs re-running
    before anything downstream can be trusted.
    """
    from_tex = read_stats_from_tex(OUT_DIRS[0])
    if not (ROUND4_ANALYSIS_DIR / "consensus_stats.json").exists():
        return from_tex, False, (
            "round4_consensus_table.tex, parsed back (UNVERIFIED)")

    from_json = read_stats_from_json(ROUND4_ANALYSIS_DIR)
    drift = sorted(k for k in set(from_json) | set(from_tex)
                   if from_json.get(k) != from_tex.get(k))
    if drift:
        raise SystemExit(
            "STALE DATA: round4_consensus_table.tex disagrees with "
            f"consensus_stats.json for {drift}.\n"
            "Re-run scripts/r4_latex_tables.py, then re-run this script.")
    return from_json, True, "consensus_stats.json (generated table agrees)"


UNVERIFIED_BANNER = """
!! ------------------------------------------------------------------ !!
!! UNVERIFIED: the Round 4 analysis output is not in this checkout.
!!   missing: {path}
!! The ratings are being read back out of round4_consensus_table.tex,
!! so this run CANNOT tell whether that table is stale with respect to
!! the ratings it was generated from. data/ is gitignored, so the source
!! exists only on the machine that ran the Round 4 pipeline.
!! ------------------------------------------------------------------ !!
"""


def resolve(stats: dict) -> list:
    """Validate statement IDs and return groups with alphabetized priorities.

    Returns [(group_heading, [priority_dict, ...]), ...]. The consensus metrics
    are attached for diagnostic reporting only; nothing here depends on them,
    which is the point (see the module docstring).
    """
    resolved = []
    for heading, entries in PRIORITY_GROUPS:
        items = []
        for name, ids, theme in entries:
            missing = [i for i in ids if i not in stats]
            if missing:
                raise SystemExit(
                    f"priority \"{name}\" cites unknown statements: {missing}")
            v = [stats[i] for i in ids]
            k = len(v)
            items.append(dict(
                name=name, ids=ids, theme=theme, k=k,
                miqr=sum(d[1] for d in v) / k,
                mmed=sum(d[0] for d in v) / k,
                zshare=sum(1 for d in v if d[1] == 0) / k,
                mn=sum(d[2] for d in v) / k,
            ))
        items.sort(key=lambda x: x["name"].lower())
        resolved.append((heading, items))

    ungloss = sorted(x["name"] for _, items in resolved for x in items
                     if x["name"] not in GLOSS)
    if ungloss:
        raise SystemExit(f"priorities with no GLOSS entry: {ungloss}")
    total = sum(len(items) for _, items in resolved)
    if total != 10:
        raise SystemExit(f"expected 10 priorities across all groups, found {total}")
    return resolved


def build_table(groups: list) -> str:
    body = []
    for gi, (heading, items) in enumerate(groups):
        if gi:
            body.append(r"\addlinespace[4pt]")
        body.append(r"\multicolumn{4}{@{}l}{\textbf{%s}}\\" % heading)
        body.append(r"\addlinespace[2pt]")
        for j, x in enumerate(items):
            if j:
                body.append(r"\addlinespace[3pt]")
            body.append("%s & %s & %s & %s (%s) \\\\" % (
                x["name"], GLOSS[x["name"]], must_act(x["ids"]),
                ", ".join(x["ids"]), x["theme"]))
    # longtable, not a table float: with the gloss and must-act columns this
    # runs past one page, and a float cannot break. Fixed p{} widths because
    # xltabular, which would give a breakable X column, is not in the TeX
    # distribution this manuscript is built with.
    header = (r"Priority & What it asks for & Must act & Supporting consensus "
              r"recommendations (topic) \\")
    return "\n".join([
        HEADER,
        r"\begingroup\footnotesize",
        r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}p{0.41\textwidth} l >{\raggedright\arraybackslash}p{0.21\textwidth}@{}}",
        r"\caption{%s}" % CAPTION,
        r"\label{tab:priorities}\\",
        r"\toprule",
        header,
        r"\midrule",
        r"\endfirsthead",
        r"\caption[]{\emph{(continued)}}\\",
        r"\toprule",
        header,
        r"\midrule",
        r"\endhead",
        r"\midrule \multicolumn{4}{r}{\emph{continued on next page}}\\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
        "\n".join(body),
        r"\end{longtable}",
        r"\endgroup",
        "",
    ])


def report(groups: list) -> None:
    print("Priorities are grouped and alphabetized within group; the consensus")
    print("metrics below are diagnostics only and do not affect the order.\n")
    print(f"{'meanIQR':>8} {'meanMed':>8} {'IQR0':>6} {'k':>2} {'meanN':>6}  priority")
    for heading, items in groups:
        print(f"\n  [{heading}]")
        for x in items:
            print(f"{x['miqr']:>8.3f} {x['mmed']:>8.3f} "
                  f"{int(x['zshare'] * x['k'])}/{x['k']:<4} {x['k']:>2} {x['mn']:>6.1f}  "
                  f"{x['name']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed tables match; write nothing")
    ap.add_argument("--allow-unverified", action="store_true",
                    help="permit writing when the Round 4 analysis output is absent "
                         "and staleness therefore cannot be ruled out")
    args = ap.parse_args()

    stats, verified, source = read_round4_stats()
    if not verified:
        print(UNVERIFIED_BANNER.format(
            path=ROUND4_ANALYSIS_DIR / "consensus_stats.json"))
        if not args.check and not args.allow_unverified:
            raise SystemExit(
                "Refusing to regenerate priorities.tex from an unverifiable source.\n"
                "Run this on the machine holding data/generated/, or pass\n"
                "--allow-unverified if you have confirmed the table is current.")
    print("ratings source:", source)
    print()
    if len(stats) != 40:
        raise SystemExit(f"expected 40 statements, parsed {len(stats)}")
    groups = resolve(stats)
    table = build_table(groups)
    report(groups)

    stale, problems = [], []
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "priorities.tex"
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != table:
                stale.append(path)
        else:
            path.write_text(table, encoding="utf-8")
            print("\nwrote", path.relative_to(PROJECT_ROOT))

    if stale:
        print("\nSTALE (re-run without --check):")
        for p in stale:
            print("  ", p.relative_to(PROJECT_ROOT))
    if problems:
        print("\nCROSS-REFERENCE PROBLEMS:")
        for p in problems:
            print("  ", p)
    if stale or problems:
        sys.exit(1)
    print("\nOK: every priority cites statements that exist in the Round 4 "
          "ratings.")


if __name__ == "__main__":
    main()
