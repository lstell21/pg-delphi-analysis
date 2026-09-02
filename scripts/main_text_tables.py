"""Generate the two tables added to the main text in response to review.

1. ``recommendations_main.tex`` -- all 40 consensus recommendations in the
   wording the panel rated, grouped by section, with the party that must act
   and the Round 4 median, IQR, and rater count. This is the paper's main
   result and sits in the manuscript itself, so it carries the full text rather
   than short labels. Wording comes from ``r4_statements``; the ratings are read
   back out of ``round4_consensus_table.tex``, so this stays in sync when the
   Round 4 pipeline is re-run.

2. ``included_studies.tex`` -- the 135 publications included in the systematic
   review, with publication type and the themes the codebook assigns. Reads the
   screening export directly and reuses ``lit_theme_synthesis`` for the theme
   assignment, so the two cannot drift apart.

Both are written to tables/. Run: python scripts/main_text_tables.py
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIRS = [
    PROJECT_ROOT / "tables",
]
LITERATURE_CSV = PROJECT_ROOT / "data" / "literature" / "articles-full-screen-results.csv"

sys.path.insert(0, str(Path(__file__).parent))
import lit_theme_synthesis as lts  # noqa: E402
import r4_statements as r4s  # noqa: E402

# ── Intended audience per recommendation ──────────────────────────────────────
# M = modelling groups, A = public health agencies, P = policy advisors.
#
# Collapsed from an earlier five-way split. Data infrastructure providers (I)
# and funders (F) are folded into A: every F statement already carried A, and
# the only I-only statements were C07 and C08, whose addressee in practice is
# the agency running the platform. "Agencies" is therefore read broadly, to
# include bodies that fund modelling or run national data infrastructure.
#
# These labels record WHO MUST ACT, not who the statement is addressed to. The
# distinction matters because the 13/27-style split in the main text reads the
# column as an actor claim ("what a modelling group can act on alone"), so a
# statement that merely names policymakers as the recipients of communication
# must not carry P. A label is assigned only where the statement text places a
# duty on that party; a party can also earn a label by hard dependency, where
# the modelling group cannot enact the statement without them (A12 and C04 need
# agency-held data, so both are M, A even though only modellers act).
#
# Confirmed against the Round 4 statement text on 2026-08-06, replacing a first
# pass that had followed the partial mapping in "Recommendations by audience"
# (\ref{sec:app:by_audience}). That pass mislabeled six statements:
#   A04  M, P -> M     policymakers appear only as recipients of communication
#   C01  M, P -> M     statement never mentions policymakers
#   C02  M, P -> M     statement never mentions policymakers
#   C03  M, P -> M     statement never mentions policymakers
#   D07  M, P -> M     statement never mentions policymakers
#   D08  M, A -> A     the actor establishing advisory boards is the agency
#   B05  M, A -> A     adopting non-traditional data sources is a surveillance
#                      decision; the agency running surveillance is the actor
# and missed a modeller duty in one A-only statement:
#   B01  A -> M, A     "document how data limitations influence model outputs"
# B07 stays A: its subordinate clause on accounting for bias "in analysis" does
# not make modellers an actor, since the statement is about surveillance design.
# C09 keeps P: it is the one statement placing a duty on policymakers, who
# "should have a foundational understanding of model uncertainty."
AUDIENCE = {
    "A01": "M",      "A02": "M",      "A03": "M",      "A04": "M",
    "A05": "M",      "A06": "M",      "A07": "M",      "A08": "M",
    "A09": "M",      "A10": "M",      "A11": "M",      "A12": "M, A",
    "A13": "M",
    "B01": "M, A", "B02": "M, A", "B03": "A",  "B04": "A",
    "B05": "A",      "B06": "A",      "B07": "A",      "B08": "A, P",
    "C01": "M",      "C02": "M",      "C03": "M",      "C04": "M, A",
    "C05": "M",      "C06": "M, A",   "C07": "A",      "C08": "A",
    "C09": "M, P",   "C10": "M, A",
    "D01": "A",   "D02": "A",   "D03": "A, P", "D04": "A",
    "D05": "M, A",   "D06": "M",      "D07": "M",      "D08": "A",
    "D09": "A",
}

SECTION_TITLES = {
    "A": "Model design and complexity",
    "B": "Data availability and quality",
    "C": "Uncertainty, validation, and communication",
    "D": "Collaboration, interdisciplinarity, and ethics",
}


# Characters pdflatex with inputenc handles without extra packages: ASCII plus
# Latin-1 accents plus the few punctuation marks below. Anything else in the
# screening export is a source artifact and is reported by --audit.
#
# U+0142 (l with stroke) used to sit in this set, which let the mangled Fisman
# title through untouched. It is a source artifact, not a character we need to
# typeset, so it is now handled by TITLE_FIXES below and rejected here.
SAFE_EXTRA = "–—‘’“”"


# ── Corrections to titles the screening export mangles ────────────────────────
# Two titles reach us damaged by the upstream export rather than by anything we
# do, and reviewers caught both in the typeset table. Repaired here so a re-run
# cannot reintroduce them; nothing else in the export is edited. The patterns
# run after tex_escape, so the replacements are final LaTeX.
#
#   Fisman (2023) carries an ellipsis that the export turned into "łdots", a
#     mangled round trip of the LaTeX "\ldots". The pattern also accepts the
#     intact ellipsis and the "..." that NFKC leaves behind, so it holds
#     whichever form a fresh export delivers.
#   Espinosa et al. (2024) carries a bracketed Spanish title whose spaces the
#     export dropped. Restored word for word; no wording is changed.
TITLE_FIXES = [
    (re.compile(r"(role of uncertainty is)(?:\u0142dots|\u2026|\.\.\.)(uncertain)",
                re.I),
     r"\1\\ldots{}\2"),
    (re.compile(r"\[Lautilidaddelosmodelosmatem\u00e1ticosenepidemiolog\u00eda"
                r"\s*paralatomadedecisionesensaludp\u00fablica\]"),
     "[La utilidad de los modelos matem\u00e1ticos en epidemiolog\u00eda "
     "para la toma de decisiones en salud p\u00fablica]"),
]


def fix_title(s: str) -> str:
    """Repair the export-mangled titles listed in TITLE_FIXES."""
    for pattern, repl in TITLE_FIXES:
        s = pattern.sub(repl, s)
    return s


def sanitize(s: str) -> str:
    """Normalize publisher-supplied text so pdflatex can typeset it.

    NFKC resolves the compatibility ligatures that appear in exported titles
    (U+2121 TELEPHONE SIGN for "TEL" turns "℡L ME" back into "TELL ME"),
    while leaving canonical accented letters composed.
    """
    return unicodedata.normalize("NFKC", s or "")


def unsupported(s: str) -> set:
    return {c for c in s
            if ord(c) > 0x7F and ord(c) > 0xFF and c not in SAFE_EXTRA}


def tex_escape(s: str) -> str:
    s = sanitize(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    # Straight quotes in source data (publication titles) typeset as upright
    # marks and reach the .docx unchanged, so pair them into TeX quotes here.
    # A typesetting transform: the words of the title are untouched.
    s = re.sub(r'"([^"]*)"', r"``\1''", s)
    return s


# ── Table 1: the 40 recommendations ───────────────────────────────────────────

def read_statements() -> dict:
    """{id: full statement text} from the canonical Round 4 registry.

    Earlier revisions of this table carried the short labels parsed out of
    consensus_recommendations.tex. The Nature Health version prints the full
    wording instead, since the statement set is the paper's main result and
    should not require the reader to open the Supplementary Information. The
    text comes from r4_statements rather than from a generated LaTeX file so
    that no escaping round-trip sits between the registry and the table.
    """
    return {i: r4s.R4_STATEMENTS[i]["text"] for i in r4s.ordered_ids()}


def read_round4_stats(tables_dir: Path) -> dict:
    """{id: (median, iqr, n, status)} from the auto-generated Round 4 table."""
    src = (tables_dir / "round4_consensus_table.tex").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
        r"^([ABCD]\d\d) & .*? & [\d.]+ \([\d.]+\) & ([\d.]+) \(([\d.]+)\) & (\d+) & (\w+)",
        src, re.M,
    ):
        out[m.group(1)] = (m.group(2), m.group(3), m.group(4), m.group(5))
    return out


def build_recommendations_table(statements: dict, stats: dict) -> str:
    rows = []
    for section in "ABCD":
        ids = sorted(i for i in statements if i.startswith(section))
        if not ids:
            continue
        rows.append(r"\multicolumn{6}{@{}l}{\textbf{Section %s: %s}}\\"
                    % (section, SECTION_TITLES[section]))
        rows.append(r"\addlinespace[2pt]")
        for i in ids:
            median, iqr, n, status = stats.get(i, ("--", "--", "--", "--"))
            rows.append(r"%s & %s & %s & %s & %s & %s \\"
                        % (i, tex_escape(statements[i]), AUDIENCE.get(i, "--"),
                           median, iqr, n))
            rows.append(r"\addlinespace[3pt]")
        rows.append(r"\addlinespace[4pt]")
    body = "\n".join(rows).rstrip()
    header = r"ID & Recommendation & Must act & Median & IQR & $n$ \\"
    return r"""%% Auto-generated by scripts/main_text_tables.py -- do not edit by hand.
\begingroup\footnotesize
\begin{longtable}{@{}l >{\raggedright\arraybackslash}p{0.52\textwidth} l c c c@{}}
\caption{\textbf{The 40 consensus recommendations.} Each statement in the wording
the panel rated, with agreement at the final rating. Statements keep the US
spelling the panel saw. Parties are M (modelling
groups), A (public health agencies, including bodies that fund modelling or run
national data infrastructure), and P (policy advisors). A party is listed where
the statement places a duty on it, or where the modelling group cannot act
without it. This assignment is our judgement, not the panel's (Supplementary
Note~9). Ratings run from 1 (strongly disagree) to 6 (strongly agree). IQR is the
interquartile range, and every statement met the criterion of IQR~$\leq$~1. $n$ is
the number of panellists who rated the statement. Supplementary Table~4 gives the
Round~3 comparison.}
\label{tab:recommendations_main}\\
\toprule
%s
\midrule
\endfirsthead
\caption[]{\emph{(continued)}}\\
\toprule
%s
\midrule
\endhead
\midrule \multicolumn{6}{r}{\emph{continued on next page}}\\
\endfoot
\bottomrule
\endlastfoot
%s
\end{longtable}
\endgroup
""" % (header, header, body)


# ── Table 2: the 135 included publications ────────────────────────────────────

THEME_SHORT = {
    "data_governance": "Data",
    "uncertainty": "Uncertainty",
    "sci_policy": "Sci-policy",
    "public_comm": "Public comm.",
    "capacity_equity": "Capacity",
    "model_dev": "Methods",
    "transparency": "Transparency",
    "reporting": "Reporting",
}


def first_author(raw: str) -> str:
    """First author's surname, plus "et al." where there are co-authors.

    The export mixes two conventions, so the comma decides which end of the
    first name holds the surname: "Cori, A; Kucharski, A" puts it before the
    comma, "Gawande MS; Zade N" puts it first.
    """
    raw = (raw or "").strip()
    if not raw:
        return "Anon."
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    head = parts[0]
    surname = head.split(",")[0].strip() if "," in head else head.split()[0].strip()
    return surname + (" et al." if len(parts) > 1 else "")


def breakable_slash(cell: str) -> str:
    """Permit a line break after each slash.

    TeX will not break or hyphenate a word containing a non-letter, so a
    slashed compound is one unbreakable box. "Perspective/Opinion" is wider
    than the 0.13\\textwidth Type column at \\scriptsize, so without this it
    overruns into the Themes column. Applied after escaping, never before.
    """
    return cell.replace("/", r"/\allowbreak ")


def build_studies_table(recs: list) -> str:
    rows = []
    for rec in sorted(recs, key=lambda r: (first_author(r.get("Author", "")).lower(),
                                           r.get("Publication Year", ""))):
        themes = [THEME_SHORT.get(k, k) for k in lts.assign(rec)]
        rows.append(r"%s & %s & %s & %s & %s \\" % (
            tex_escape(first_author(rec.get("Author", ""))),
            tex_escape((rec.get("Publication Year") or "").strip() or "n.d."),
            fix_title(tex_escape((rec.get("Title") or "").strip())),
            breakable_slash(tex_escape((rec.get("Type") or "").strip() or "--")),
            tex_escape(", ".join(sorted(themes)) or "--"),
        ))
        rows.append(r"\addlinespace[1pt]")
    body = "\n".join(rows).rstrip()
    return r"""%% Auto-generated by scripts/main_text_tables.py -- do not edit by hand.
\begingroup\scriptsize
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.17\textwidth} l >{\raggedright\arraybackslash}p{0.29\textwidth} >{\raggedright\arraybackslash}p{0.13\textwidth} >{\raggedright\arraybackslash}p{0.19\textwidth}@{}}
\caption{\textbf{Publications included in the systematic review.} The %d
publications included, with the
publication type recorded during screening and the themes the term-based
codebook (\protect\hyperref[sec:app:coding]{Supplementary Note~17}) assigns from the extracted challenge and
recommendation text. Themes are not mutually exclusive. A dash means the
codebook matched no theme term, not that the publication addresses none.}
\label{tab:included_studies}\\
\toprule
First author & Year & Title & Type & Themes \\
\midrule
\endfirsthead
\caption[]{\emph{(continued)}}\\
\toprule
First author & Year & Title & Type & Themes \\
\midrule
\endhead
\midrule \multicolumn{5}{r}{\emph{continued on next page}}\\
\endfoot
\bottomrule
\endlastfoot
%s
\end{longtable}
\endgroup
""" % (len(recs), body)


def main() -> None:
    tables_dir = OUT_DIRS[0]
    statements = read_statements()
    stats = read_round4_stats(tables_dir)
    if len(statements) != 40 or len(stats) != 40:
        raise SystemExit(f"error: expected 40 statements, got {len(statements)} "
                         f"statements and {len(stats)} stat rows")
    rec_table = build_recommendations_table(statements, stats)

    recs = lts.load(LITERATURE_CSV)
    if len(recs) != 135:
        raise SystemExit(f"error: expected 135 included publications, got {len(recs)}")
    studies_table = build_studies_table(recs)
    leftover = unsupported(studies_table)
    if leftover:
        raise SystemExit("error: characters pdflatex cannot typeset: "
                         + " ".join(f"U+{ord(c):04X}" for c in sorted(leftover, key=ord)))

    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "recommendations_main.tex").write_text(rec_table, encoding="utf-8")
        (out_dir / "included_studies.tex").write_text(studies_table, encoding="utf-8")
        print(f"wrote {out_dir / 'recommendations_main.tex'}")
        print(f"wrote {out_dir / 'included_studies.tex'}")


if __name__ == "__main__":
    main()
