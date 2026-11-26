#!/usr/bin/env python3
"""
PRISMA 2020 flow diagram of the systematic review (Fig. 2).

Redraws the PRISMA 2020 template for new systematic reviews that searched
databases and registers only (Page et al. 2021), laid out as in
PRISMA_2020_flow_diagram_PG_v2.docx, at print size in the shared figure style.
The template's title and its three footnotes are in the figure legend.

It draws the figure from data/literature/prisma_counts.csv, which the data
deposit carries. The counts were derived from the screening records by a
mode this release omits, because the Rayyan export it reads is not
deposited. Where the counts come from:
- Identification. The database search returned 2,216 records, and Rayyan's
  de-duplication removed 439. The search exports are not in the repository,
  so SEARCH_STAGE records these two numbers. No register was searched, and no
  record was removed by automation tools or for other reasons.
- Title and abstract screening. literature/rayyan-screened-export.csv holds
  the records that passed it, so the screened records less these are the
  records excluded.
- Full text. In the same file, a record whose exclusion reason is "not
  retrieved" was sought but not retrieved, and every other record was assessed.
  The criteria an excluded report failed are its RAYYAN-EXCLUSION-REASONS.
- Reassessment. literature/articles-full-screen-results.csv holds the reports
  reassessed against the refined criteria, with Decision and Failed Criteria.
  The reports excluded at full text are the assessed reports that did not enter
  the reassessment.
"""
import argparse
import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.textpath import TextPath

PROJECT_ROOT = Path(__file__).resolve().parent.parent
from utils import figstyle

figstyle.apply()

COUNTS = PROJECT_ROOT / "data" / "literature" / "prisma_counts.csv"
OUT = PROJECT_ROOT / "figures" / "prisma_flow.pdf"


# Short names of the five eligibility criteria, as the Methods refer to them.
CRITERIA = {1: "human infectious disease", 2: "model-based approach", 3: "public health relevance",
            4: "critical discussion", 5: "broader perspective"}
SHOW_CRITERION_NAMES = True


# --------------------------------------------------------------------- counts


def read_counts(path: Path) -> dict:
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["count"]: int(r["n"]) for r in csv.DictReader(fh)}


# --------------------------------------------------------------------- figure
LINE = 3.3       # mm per text line at 8 pt
PAD = 1.5        # mm above and below a text block
INDENT = 3.2     # mm, the template's indented sub-lines
GAP = 3.6        # mm between boxes in a column
W_FIG = figstyle.TEXT_WIDTH_IN * 25.4
BAR_X, BAR_W = 1.2, 6.6
LX, LW = 11.0, 52.0                  # left column
RX = LX + LW + 7.0                   # right column
RW = W_FIG - RX - 1.2
EDGE = 1.0                           # pt, box outlines
BAR_LABEL_MARGIN = 3.0              # mm left free beyond a rotated phase label
FS = figstyle.check_size(8.0)
HEADER_FILL, HEADER_EDGE = "#FFC000", "#BF9000"
BAR_FILL, BAR_EDGE = "#9DC3E6", "#41719C"


def n(x: int) -> str:
    return f"(n = {x:,})"


def label_mm(text: str) -> float:
    """Length in mm of a bold phase label at FS, which sets its bar's minimum height."""
    prop = FontProperties(family="sans-serif", weight="bold")   # resolves through figstyle, as the drawn text does
    return TextPath((0, 0), text, size=FS, prop=prop).get_extents().width * 25.4 / 72


def height(lines) -> float:
    return len(lines) * LINE + 2 * PAD


class Drawer:
    def __init__(self, ax, fig):
        self.ax, self.fig = ax, fig
        self.renderer = fig.canvas.get_renderer()
        self.overruns = []

    def width_mm(self, artist) -> float:
        bb = artist.get_window_extent(self.renderer)
        inv = self.ax.transData.inverted()
        return abs(inv.transform((bb.x1, 0))[0] - inv.transform((bb.x0, 0))[0])

    def box(self, x, y, w, h):
        self.ax.add_patch(Rectangle((x, y), w, h, fill=True, facecolor="white",
                                    edgecolor="black", linewidth=EDGE, zorder=2))

    def rounded(self, x, y, w, h, fc, ec):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                         facecolor=fc, edgecolor=ec, linewidth=0.8, zorder=2))

    def text(self, x, y, w, h, lines):
        """lines: (indent level, runs); runs are (text, style) or the string 'rule'."""
        top = y + (h - len(lines) * LINE) / 2
        for i, (level, runs) in enumerate(lines):
            cy = top + (i + 0.5) * LINE
            cx = x + 2.4 + level * INDENT
            if runs == "rule":
                self.ax.plot([cx, cx + 34.0], [cy, cy], color="black", linewidth=0.5,
                             linestyle=(0, (2.2, 1.6)), zorder=3)
                continue
            for txt, style in runs:
                t = self.ax.text(cx, cy, txt, fontsize=FS, va="center", ha="left", zorder=3,
                                 fontstyle="italic" if style == "i" else "normal")
                cx += self.width_mm(t)
            if cx > x + w - 1.0:
                self.overruns.append("".join(r[0] for r in runs))

    def arrow(self, x0, y0, x1, y1):
        self.ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=7,
                                          linewidth=0.8, color="black", shrinkA=0, shrinkB=0, zorder=4))


def criteria_lines(head, overall, counts, prefix):
    lines = [(0, [(head, "n")]), (1, [(f"Overall*** {n(overall)}", "n")]), (1, "rule")]
    for k, name in CRITERIA.items():
        label = f"Criterion {k}, {name}" if SHOW_CRITERION_NAMES else f"Criterion {k}"
        lines.append((1, [(f"{label} {n(counts[f'{prefix}_c{k}'])}", "n")]))
    return lines


def draw(c: dict, out: Path) -> list:
    L = {
        "ident": [(0, [("Records identified from:", "n")]),
                  (1, [(f"Databases {n(c['identified_databases'])}", "n")]),
                  (1, [(f"Registers {n(c['identified_registers'])}", "n")])],
        "removed": [(0, [(r"Records removed $\mathit{before\ screening}$:", "n")]),
                    (1, [(f"Duplicate records removed {n(c['duplicates_removed'])}", "n")]),
                    (1, [("Records marked as ineligible by automation", "n")]),
                    (1, [(f"tools {n(c['automation_removed'])}", "n")]),
                    (1, [(f"Records removed for other reasons {n(c['other_removed'])}", "n")])],
        "screened": [(0, [("Records screened", "n")]), (0, [(n(c["screened"]), "n")])],
        "excl_ta": [(0, [("Records excluded*", "n")]), (0, [(n(c["excluded_screening"]), "n")])],
        "sought": [(0, [("Reports sought for retrieval", "n")]), (0, [(n(c["sought"]), "n")])],
        "not_ret": [(0, [("Reports not retrieved", "n")]), (0, [(n(c["not_retrieved"]), "n")])],
        "assessed": [(0, [("Reports assessed for eligibility**", "n")]), (0, [(n(c["assessed"]), "n")])],
        "excl_ft": criteria_lines("Reports excluded:", c["excluded_fulltext"], c, "excluded_fulltext"),
        "refined": [(0, [("Refined criteria for eligibility", "n")]), (0, [("assessment", "n")])],
        "reassessed": [(0, [("Reports re-assessed for", "n")]), (0, [("eligibility**", "n")]),
                       (0, [(n(c["reassessed"]), "n")])],
        "excl_re": criteria_lines("Reports excluded on re-assessment:", c["excluded_reassessment"], c,
                                  "excluded_reassessment"),
        "included": [(0, [("Reports of included studies", "n")]), (0, [(n(c["included"]), "n")])],
    }
    # Vertical layout in mm, measured downwards from the top edge.
    y_head, h_head = 1.2, 7.4
    y = y_head + h_head + 2.8
    rows = {}
    # Tall enough for the text and for the rotated "Identification" in its bar.
    h = max(height(L["ident"]), height(L["removed"]), label_mm("Identification") + BAR_LABEL_MARGIN)
    rows["ident"] = rows["removed"] = (y, h); y += h + GAP
    for left, right in (("screened", "excl_ta"), ("sought", "not_ret")):
        h = max(height(L[left]), height(L[right]))
        rows[left] = rows[right] = (y, h); y += h + GAP
    h_r = height(L["excl_ft"])
    rows["excl_ft"] = (y, h_r)
    rows["assessed"] = (y, height(L["assessed"]))
    rows["refined"] = (y + h_r - height(L["refined"]), height(L["refined"]))
    y += h_r + GAP
    h_r = height(L["excl_re"])
    rows["excl_re"] = (y, h_r)
    rows["reassessed"] = (y, height(L["reassessed"]))
    # The included box sits below the re-assessed one and is tall enough for its
    # rotated "Included" bar, so it may reach below the right column.
    h_inc = max(height(L["included"]), label_mm("Included") + BAR_LABEL_MARGIN)
    rows["included"] = (y + height(L["reassessed"]) + GAP, h_inc)
    h_fig = max(y + h_r, rows["included"][0] + h_inc) + 1.2

    fig = plt.figure(figsize=(W_FIG / 25.4, h_fig / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_FIG); ax.set_ylim(h_fig, 0); ax.axis("off")
    d = Drawer(ax, fig)

    d.rounded(LX, y_head, RX + RW - LX, h_head, HEADER_FILL, HEADER_EDGE)
    ax.text(LX + (RX + RW - LX) / 2, y_head + h_head / 2, "Identification of studies via databases and registers",
            fontsize=FS, fontweight="bold", ha="center", va="center", zorder=3)
    phases = [("Identification", rows["ident"][0], rows["ident"][0] + rows["ident"][1]),
              ("Screening", rows["screened"][0], rows["reassessed"][0] + rows["reassessed"][1]),
              ("Included", rows["included"][0], rows["included"][0] + rows["included"][1])]
    for label, top, bottom in phases:
        d.rounded(BAR_X, top, BAR_W, bottom - top, BAR_FILL, BAR_EDGE)
        ax.text(BAR_X + BAR_W / 2, (top + bottom) / 2, label, rotation=90, fontsize=FS,
                fontweight="bold", ha="center", va="center", zorder=3)

    left = ["ident", "screened", "sought", "assessed", "refined", "reassessed", "included"]
    right = {"ident": "removed", "screened": "excl_ta", "sought": "not_ret",
             "assessed": "excl_ft", "reassessed": "excl_re"}
    for key in left:
        top, h = rows[key]; d.box(LX, top, LW, h); d.text(LX, top, LW, h, L[key])
    for lkey, rkey in right.items():
        top, h = rows[rkey]; d.box(RX, top, RW, h); d.text(RX, top, RW, h, L[rkey])
        ltop, lh = rows[lkey]
        d.arrow(LX + LW, ltop + lh / 2, RX, ltop + lh / 2)
    for a, b in zip(left, left[1:]):
        (ta, ha), (tb, _) = rows[a], rows[b]
        d.arrow(LX + LW / 2, ta + ha, LX + LW / 2, tb)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="pdf", metadata={"CreationDate": None})
    fig.savefig(out.with_suffix(".png"), format="png", dpi=200)
    plt.close(fig)
    return d.overruns


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--counts", type=Path, default=COUNTS)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    c = read_counts(args.counts)
    overruns = draw(c, args.out)
    if overruns:
        raise SystemExit("text runs past its box: " + "; ".join(overruns))
    print("wrote", args.out, "and", args.out.with_suffix(".png").name)
    for k, v in c.items():
        print(f"  {k:28s} {v:>6,}")


if __name__ == "__main__":
    main()
