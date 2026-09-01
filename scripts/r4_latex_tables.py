"""
Round 4 stage 7: LaTeX table and comparison figure.

Generates:
  * tables/round4_consensus_table.tex  -> tab:final_consensus
      A longtable (booktabs) grouped by section: ID, full statement text,
      Round 3 median (IQR), Round 4 median (IQR), n, consensus status.
      This used to be two tables, one abbreviated and one with the full
      wording, whose numeric columns were identical. They are now one.
  * tables/rankings.tex               -> tab:rankings
      The Section E ranking task: all seven preparedness measures across all
      three phases, with per-measure n, first-choice count, mean rank, and
      Borda total. Built from r4_rankings.py's rankings.json.
  * figures/round4_comparison.pdf     -> fig:round4_comparison
      A per-statement dumbbell plot of IQR (Round 3 -> Round 4) with the
      consensus (IQR<=1) and near-consensus (IQR<=1.5) zones shaded, showing the
      collapse in dispersion at the final round.

These are \\input / \\includegraphics-ed by the Nature Health manuscript and its
Supplementary Information.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import ROUND4_ANALYSIS_DIR, ROUND4_RESPONSES, PROJECT_ROOT
from r4_statements import R4_STATEMENTS, SECTION_NAMES, ordered_ids

TABLES_DIR = PROJECT_ROOT / "tables"
FIGURES_DIR = PROJECT_ROOT / "figures"

# The lists stay lists so a second output target can be added without
# touching write_table or write_figure.
TABLES_DIRS = [TABLES_DIR]
FIGURES_DIRS = [FIGURES_DIR]


def write_table(name, text, kind="table"):
    """Write one generated file into every manuscript's tables directory."""
    for d in TABLES_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        with open(d / name, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[OK] LaTeX {kind} -> {d / name}")

STATUS_LABEL = {
    "consensus": "Consensus",
    "near-consensus": "Near-consensus",
    "non-consensus": "Non-consensus",
}


def tex_escape(s: str) -> str:
    repl = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def fmt(median, iqr):
    """Format 'median (IQR)' with tidy numbers (6 not 6.0; 0.5 kept)."""
    def n(x):
        x = float(x)
        return str(int(x)) if x == int(x) else f"{x:g}"
    return f"{n(median)} ({n(iqr)})"


# Panel-characteristics groups: (group title, demographic field, ordered list of
# (label as stored in the extracted JSON, display label for the table)). Categories
# with a zero count are omitted from the rendered table.
PANEL_GROUPS = [
    ("Geographic region of primary affiliation", "region", [
        ("Europe", "Europe"),
        ("North America", "North America"),
        ("Latin America & Caribbean", "Latin America and the Caribbean"),
        ("Asia-Pacific", "Asia-Pacific"),
        ("South Asia", "South Asia"),
        ("Middle East & North Africa", "Middle East and North Africa"),
        ("Sub-Saharan Africa", "Sub-Saharan Africa"),
        ("Oceania", "Oceania"),
    ]),
    ("Professional background", "background", [
        ("Academic / Researcher", "Academic / researcher"),
        ("Clinician / Practitioner", "Clinician / practitioner"),
        ("Public health / Policy / Government", "Public health / policy / government"),
        ("Industry / Private sector", "Industry / private sector"),
        ("Regulatory affairs", "Regulatory affairs"),
        ("NGO / Non-profit", "NGO / non-profit"),
        ("Patient / Lived experience representative", "Patient / lived-experience representative"),
    ]),
    ("Employment sector", "sector", [
        ("University / Research institute", "University / research institute"),
        ("Hospital / Health system", "Hospital / health system"),
        ("Government / Public agency", "Government / public agency"),
        ("International organization (e.g., WHO, ECDC)", "International organization"),
        ("NGO / Non-profit", "NGO / non-profit"),
        ("Private industry", "Private industry"),
        ("Independent practice / Self-employed", "Independent practice / self-employed"),
    ]),
    ("Career stage (current position)", "position", [
        ("Full Professor / Senior researcher", "Full professor / senior researcher"),
        ("Associate Professor / Senior lecturer", "Associate professor / senior lecturer"),
        ("Assistant Professor / Junior faculty / Lecturer", "Assistant professor / junior faculty"),
        ("Postdoctoral researcher", "Postdoctoral researcher"),
        ("PhD candidate / Doctoral researcher", "Doctoral researcher"),
        ("Emeritus / Retired", "Emeritus / retired"),
        ("Non-academic professional (clinical, policy, industry)", "Non-academic professional"),
    ]),
    ("Years of professional experience in the field", "experience", [
        ("More than 20 years", "More than 20 years"),
        ("11 to 20 years", "11 to 20 years"),
        ("5 to 10 years", "5 to 10 years"),
        ("Less than 5 years", "Less than 5 years"),
    ]),
    ("Self-rated expertise", "expertise", [
        # Left element matches the raw survey export verbatim; right element is our
        # display label, so it follows the manuscript's British spelling.
        ("Recognized expert with leadership in this field", "Recognised expert / leadership"),
        ("Extensive experience and active involvement", "Extensive / active involvement"),
        ("Substantial experience in this field", "Substantial experience"),
        ("Some experience, but limited depth", "Some / limited depth"),
        ("No significant experience in this field", "No significant experience"),
    ]),
    ("Published on the topic within the past 5 years", "publications", [
        ("Yes", "Yes"),
        ("No", "No"),
    ]),
]


def _pct_round(n: int, total: int) -> int:
    """Percentage of total, rounded half up to a whole number."""
    import math
    return int(math.floor(n / total * 100 + 0.5))


# Groups carried by the short version's trimmed table. The rest (professional
# background, self-rated expertise, recent publication) stay in the extended
# table only. Keeping this as a subset of PANEL_GROUPS rather than a separate
# hand-maintained file means the two cannot drift apart.
BRIEF_GROUPS = ("Geographic region of primary affiliation", "Employment sector",
                "Career stage (current position)",
                "Years of professional experience in the field")


def build_panel_table(submissions, groups=None, label="tab:panel_characteristics",
                      brief=False) -> str:
    from collections import Counter

    groups = groups or PANEL_GROUPS

    # Panel characteristics describe the panellists who *completed* the final round
    # -- a clean, duplicate-free denominator. Per the pre-registration, partial
    # responses are still included per statement in the consensus statistics
    # (where the per-statement n is reported), but they are not characterised here.
    completers = [s for s in submissions if s.get("complete", True)]
    total = len(completers)
    counts = {field: Counter(s["demographics"].get(field) for s in completers)
              for _, field, _ in groups}

    # Type size and column type differ between the two variants, and both used to
    # be hand-applied to the generated file after every run, under a "re-apply
    # after regenerating" comment that every regeneration silently dropped. They
    # are emitted here instead, so running this script is idempotent.
    #
    # The extended table carries all seven groups, so it needs \footnotesize and
    # a ragged-right paragraph column to fit one page without underfull lines.
    # The trimmed variant carries four groups and stays at the more readable
    # \small, where justified text still sets cleanly.
    size = r"\small" if brief else r"\footnotesize"
    xcol = "X" if brief else r">{\raggedright\arraybackslash}X"

    lines = []
    lines.append("% Auto-generated by scripts/r4_latex_tables.py -- do not edit by hand.")
    if not brief:
        lines.append(r"%% Nature Health copy: \footnotesize with a ragged-right paragraph")
        lines.append(r"%% column, so the float fits one page and short entries do not leave")
        lines.append(r"%% underfull lines. Set in build_panel_table, not by hand.")
    lines.append(r"\begin{table}[!htbp]")
    lines.append(r"\centering")
    # Both variants carry career stage, so the academic-titles caveat belongs to
    # both. Only the full table has self-rated expertise; only the brief one
    # needs to say where the omitted groups went.
    notes = [r"The career-stage categories use one common set of academic titles, which do not "
             r"map identically onto every national system."]
    if brief:
        notes.append(r"Professional background, self-rated expertise, and recent publication on "
                     r"the topic are reported in the extended version of this table "
                     r"(Table~\ref{tab:panel_characteristics}).")
    else:
        notes.append(r"Self-rated expertise is the panellist's own assessment rather than an "
                     r"external judgement.")
    lines.append(rf"\caption{{\textbf{{Composition of the expert panel.}} Characteristics of the {total} panellists who completed the final "
                 rf"Round~4 rating. Panellists selected from pre-defined response options for "
                 rf"every item. {' '.join(notes)} Percentages are of these "
                 rf"{total} completers and may not sum to 100 due to rounding.}}"
                 rf"\label{{{label}}}")
    lines.append(rf"\begingroup{size}")
    lines.append(rf"\begin{{tabularx}}{{\textwidth}}{{{xcol} r r}}")
    lines.append(r"\toprule")
    lines.append(r"Characteristic (self-reported) & $n$ & \% \\")
    lines.append(r"\midrule")

    for gi, (title, field, cats) in enumerate(groups):
        if gi > 0:
            lines.append(r"\addlinespace[4pt]")
        lines.append(rf"\multicolumn{{3}}{{@{{}}l}}{{\textit{{{tex_escape(title)}}}}}\\")
        lines.append(r"\addlinespace[2pt]")
        for data_label, display in cats:
            n = counts[field].get(data_label, 0)
            if n == 0:
                continue
            lines.append(rf"\quad {tex_escape(display)} & {n} & {_pct_round(n, total)} \\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabularx}")
    lines.append(r"\endgroup")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


def build_recommendations_list() -> str:
    """Compact consensus-recommendation list (enumerate per section), short labels.

    Renders tab:final_consensus's statements as the paper's recommendations,
    grouped under the four thematic sections and keyed by statement id. Only the
    short label is shown here to keep the body concise; the full wording of each
    recommendation lives in the appendix table tab:final_consensus.
    """
    lines = []
    lines.append("% Auto-generated by scripts/r4_latex_tables.py -- do not edit by hand.")
    for sec in ["A", "B", "C", "D"]:
        lines.append(rf"\subsubsection*{{Section {sec}: {tex_escape(SECTION_NAMES[sec])}}}")
        lines.append(r"\begin{enumerate}")
        for sid in ordered_ids():
            if R4_STATEMENTS[sid]["section"] != sec:
                continue
            label = tex_escape(R4_STATEMENTS[sid]["short_label"])
            lines.append(rf"  \item \textbf{{{sid}:}} {label}")
        lines.append(r"\end{enumerate}")
    return "\n".join(lines) + "\n"


def build_statements_appendix(consensus, comparison) -> str:
    """Full Delphi statement list with round-by-round agreement (longtable).

    Columns: ID, full statement text, Round 3 median (IQR), Round 4 median (IQR),
    consensus status. Grouped by section. Round 4 figures come from
    consensus_stats.json; Round 3 figures from round3_vs_round4.json.
    """
    lines = []
    lines.append("% Auto-generated by scripts/r4_latex_tables.py -- do not edit by hand.")
    lines.append(r"\begingroup\footnotesize")
    lines.append(r"\begin{longtable}{@{}l >{\raggedright\arraybackslash}p{0.48\textwidth} c c c l@{}}")
    lines.append(r"\caption{\textbf{Statement-level agreement across the final two rounds.} "
                 r"All 40 statements at both quantitative rounds. "
                 r"The R3 and R4 columns give the median rating with the interquartile range "
                 r"(IQR) in parentheses, and the R3 figures pool the two pairs of statements "
                 r"merged after Round~3. $n$ is the number of panellists who rated each "
                 r"statement, excluding ``Not qualified to respond'' and non-responses, and "
                 r"varies because partial completions were retained. Consensus is based on the "
                 r"IQR of the six-point ratings: "
                 r"IQR~$\leq$~1 (consensus), $1<$~IQR~$\leq$~1.5 (near-consensus), "
                 r"IQR~$>$~1.5 (non-consensus).}"
                 r"\label{tab:final_consensus}\\")
    lines.append(r"\toprule")
    header = r"ID & Statement & R3 & R4 & $n$ & Status \\"
    lines.append(header)
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(r"\caption[]{\emph{(continued)}}\\")
    lines.append(r"\toprule")
    lines.append(header)
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\midrule \multicolumn{6}{r}{\emph{continued on next page}}\\")
    lines.append(r"\endfoot")
    lines.append(r"\bottomrule")
    lines.append(r"\endlastfoot")

    for sec in ["A", "B", "C", "D"]:
        lines.append(rf"\multicolumn{{6}}{{@{{}}l}}{{\textbf{{Section {sec}: "
                     rf"{tex_escape(SECTION_NAMES[sec])}}}}}\\")
        lines.append(r"\addlinespace[2pt]")
        for sid in ordered_ids():
            if R4_STATEMENTS[sid]["section"] != sec:
                continue
            cs = consensus["statements"][sid]
            cmp_row = comparison["statements"][sid]
            text = tex_escape(R4_STATEMENTS[sid]["text"])
            r3 = fmt(cmp_row["r3_median"], cmp_row["r3_iqr"])
            r4 = fmt(cs["median"], cs["iqr"])
            status = STATUS_LABEL[cs["consensus_class"]]
            lines.append(rf"{sid} & {text} & {r3} & {r4} & {cs['n_rated']} & {status} \\")
            lines.append(r"\addlinespace[2pt]")
        lines.append(r"\addlinespace[4pt]")

    lines.append(r"\end{longtable}")
    lines.append(r"\endgroup")
    return "\n".join(lines) + "\n"


def build_rankings_table(rankings) -> str:
    """Section E ranking task: all seven measures, all three phases (longtable).

    Rows are grouped by phase and ordered within a phase by mean rank, which is
    the ordering r4_rankings.py already applies. Columns give the per-measure n,
    the first-choice count, the mean rank, and the Borda total.

    A longtable rather than a float: it follows the 40-row tab:final_consensus
    in the same Supplementary Note, and a float that size would be deferred past
    the end of the note.
    """
    lines = []
    lines.append("% Auto-generated by scripts/r4_latex_tables.py -- do not edit by hand.")
    lines.append(r"\begingroup\footnotesize")
    # 0.60\textwidth keeps all but the longest measure name on a single line,
    # which is what lets the three phase blocks share one page.
    lines.append(r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.60\textwidth} r r r r@{}}")
    lines.append(r"\caption{\textbf{Ranking of preparedness measures by pandemic phase.} "
                 r"The Round~4 ranking task, in which panellists ordered the same seven "
                 r"measures by importance for each of three phases, rank~1 being the most "
                 r"important. Measures are listed by mean rank within each phase. "
                 r"``First'' counts the "
                 r"panellists who ranked a measure first. Borda awards $8-r$ points for rank "
                 r"$r$, so a higher total means a measure was preferred. Because it is a sum "
                 r"rather than an average, it can order two measures differently from the "
                 r"mean rank when their $n$ differ. $N$ is the number of panellists who "
                 r"ranked a phase at all, and $n$ the number who ranked that particular "
                 r"measure. This task measured stated importance, unlike the statement "
                 r"ratings in Supplementary Table~\ref{tab:final_consensus}, which measure "
                 r"agreement.}"
                 r"\label{tab:rankings}\\")
    lines.append(r"\toprule")
    header = r"Preparedness measure & $n$ & First & Mean rank & Borda \\"
    lines.append(header)
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(r"\caption[]{\emph{(continued)}}\\")
    lines.append(r"\toprule")
    lines.append(header)
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\midrule \multicolumn{5}{r}{\emph{continued on next page}}\\")
    lines.append(r"\endfoot")
    lines.append(r"\bottomrule")
    lines.append(r"\endlastfoot")

    phases = rankings["phases"]
    for pi, (phase, pdata) in enumerate(phases.items()):
        if pi > 0:
            lines.append(r"\addlinespace[6pt]")
        # The stored description is a sentence fragment ("Before an epidemic or
        # pandemic emerges"); it reads as the phase name with the respondent
        # count appended.
        desc = tex_escape(pdata["description"])
        # \\* forbids a page break after a row, so a phase block cannot be split
        # across pages: only the last row of a block ends with a plain \\. The
        # table runs to two pages, and without this the break lands inside a
        # block and strands a measure under the wrong phase heading.
        # p{} rather than l: the longest phase heading does not fit on one
        # line, and an l column cannot wrap, so it would set the width of
        # the whole longtable and push it past \textwidth.
        lines.append(rf"\multicolumn{{5}}{{@{{}}p{{\linewidth}}@{{}}}}{{\textbf{{{desc}}} "
                     rf"($N$~=~{pdata['n_respondents']} panellists)}}\\*")
        lines.append(r"\addlinespace[2pt]")
        last = len(pdata["items"]) - 1
        for i, it in enumerate(pdata["items"]):
            # Item texts are stored with a trailing period, which reads as a typo
            # in a table cell.
            text = tex_escape(it["text"].rstrip("."))
            mean = "--" if it["mean_rank"] is None else f"{it['mean_rank']:.2f}"
            end = r"\\" if i == last else r"\\*"
            lines.append(rf"{text} & {it['n_ranked']} & {it['first_choice']} & "
                         rf"{mean} & {it['borda']} {end}")

    lines.append(r"\end{longtable}")
    lines.append(r"\endgroup")
    return "\n".join(lines) + "\n"


def build_figure(comparison):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    ids = ordered_ids()
    # Plot top-to-bottom in section order.
    y = list(range(len(ids), 0, -1))
    r3 = [comparison["statements"][s]["r3_iqr"] for s in ids]
    r4 = [comparison["statements"][s]["r4_iqr"] for s in ids]

    fig, ax = plt.subplots(figsize=(7.0, 10.0))
    # Consensus zones.
    ax.axvspan(0, 1.0, color="#2ca02c", alpha=0.08, zorder=0)
    ax.axvspan(1.0, 1.5, color="#ff7f0e", alpha=0.08, zorder=0)
    ax.axvline(1.0, color="#2ca02c", lw=1, ls="--", zorder=1)
    ax.axvline(1.5, color="#ff7f0e", lw=1, ls="--", zorder=1)

    for yi, a, b in zip(y, r3, r4):
        ax.plot([a, b], [yi, yi], color="#bbbbbb", lw=1.2, zorder=2)
    ax.scatter(r3, y, s=26, color="#7f7f7f", label="Round 3", zorder=3)
    ax.scatter(r4, y, s=30, color="#1f77b4", label="Round 4", zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels(ids, fontsize=7)
    ax.set_xlabel("Interquartile range (IQR) of ratings")
    ax.set_xlim(-0.1, 4.2)
    ax.set_title("Dispersion of agreement by statement: Round 3 → Round 4")

    # Section separators.
    sec_of = {s: R4_STATEMENTS[s]["section"] for s in ids}
    for i in range(1, len(ids)):
        if sec_of[ids[i]] != sec_of[ids[i - 1]]:
            ax.axhline(y[i] + 0.5, color="#dddddd", lw=0.8)

    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#7f7f7f", markersize=7, label="Round 3"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#1f77b4", markersize=7, label="Round 4"),
        Line2D([0], [0], color="#2ca02c", ls="--", label="Consensus (IQR ≤ 1)"),
        Line2D([0], [0], color="#ff7f0e", ls="--", label="Near-consensus (IQR ≤ 1.5)"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.9)
    ax.grid(axis="x", color="#eeeeee", zorder=0)
    fig.tight_layout()

    # Render once and copy, rather than saving per directory: matplotlib stamps
    # the wall clock into the PDF's CreationDate, so two saves a second apart
    # produce byte-different files and the two manuscripts look out of sync.
    #
    # CreationDate=None drops that stamp altogether, which makes the PDF
    # byte-identical between runs on unchanged data. Without it every run of
    # this script dirties the figure in git with a diff that has no content
    # behind it. The PNG carries no timestamp, so it needs no equivalent.
    FIGURES_DIRS[0].mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIRS[0] / "round4_comparison.pdf"
    fig.savefig(out, bbox_inches="tight", metadata={"CreationDate": None})
    # PNG sibling for the Word export (pandoc cannot embed PDF in docx).
    fig.savefig(out.with_suffix(".png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    for d in FIGURES_DIRS[1:]:
        d.mkdir(parents=True, exist_ok=True)
        for src in (out, out.with_suffix(".png")):
            shutil.copyfile(src, d / src.name)
    return out


def main():
    with open(ROUND4_ANALYSIS_DIR / "consensus_stats.json", encoding="utf-8") as f:
        consensus = json.load(f)
    with open(ROUND4_ANALYSIS_DIR / "round3_vs_round4.json", encoding="utf-8") as f:
        comparison = json.load(f)

    write_table("round4_consensus_table.tex",
                build_statements_appendix(consensus, comparison))

    with open(ROUND4_RESPONSES, encoding="utf-8") as f:
        extracted = json.load(f)
    write_table("panel_characteristics.tex", build_panel_table(extracted["submissions"]))

    # Trimmed variant for the short version, from the same submissions so the
    # two cannot disagree.
    # panel_characteristics_brief.tex and consensus_recommendations.tex are no
    # longer part of the manuscript: the brief panel table was superseded by the
    # Extended Data table, and the short-label recommendation list duplicated main
    # Table 1 and Supplementary Table 4, so its Supplementary Note was cut. The
    # builders are kept so those tables can still be regenerated.

    with open(ROUND4_ANALYSIS_DIR / "rankings.json", encoding="utf-8") as f:
        rankings = json.load(f)
    write_table("rankings.tex", build_rankings_table(rankings))

    try:
        fig_path = build_figure(comparison)
        print(f"[OK] Comparison figure -> {fig_path}")
    except Exception as e:
        print(f"[INFO] Figure generation skipped ({e}). Install matplotlib to enable.")


if __name__ == "__main__":
    main()
