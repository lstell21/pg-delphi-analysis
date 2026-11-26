#!/usr/bin/env python3
"""
Generate Delphi process flowchart.

Usage:
    python scripts/generate_delphi_flowchart.py

Output:
    figures/delphi_flowchart.pdf
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from utils import figstyle

figstyle.apply()

# ── Output path ────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURES_DIR = os.path.join(SCRIPT_DIR, '..', 'figures')

# A second output target can be added to OUT_DIRS without other changes.
OUT_DIRS = [
    FIGURES_DIR,
]
OUT_NAME = 'delphi_flowchart'

# ── Design constants ───────────────────────────────────────────────────────────

# The axes fill the canvas, so one data unit is one inch at print size. The
# chart is as wide as the manuscript's text block and is included in LaTeX at
# natural size, so every letter prints at 8 pt or more (CH-41).
FIG_W, FIG_H = figstyle.TEXT_WIDTH_IN, 5.92   # inches
CX      = FIG_W / 2         # horizontal centre of all boxes
BOX_W   = 5.0               # box width
BOX_W_SM = 4.5              # width of smaller start/end boxes (must fit their text)

# Colors
C_START  = '#D6EAF8'   # pale blue  – starting node
C_ROUND  = '#EBF5EB'   # pale green – Delphi rounds
C_FINAL  = '#FEF9E7'   # pale amber – final output
C_BSTART = '#2471A3'   # blue border
C_BROUND = '#196F3D'   # green border (darkened for contrast, CH-41)
C_BFINAL = '#9A7D0A'   # amber border
C_TSTART = '#1A5276'   # blue title text
C_TROUND = '#196F3D'   # green title text
C_TFINAL = '#7D6608'   # amber title text
C_TEXT   = '#2C3E50'   # body text
C_SUB    = '#626567'   # subtitle text
C_ARROW  = '#566573'   # arrow colour
C_REV    = '#5D6D7E'   # revision label text (darkened for contrast, CH-41)

# Typography: nothing under 8 pt
FS_TITLE = figstyle.check_size(9.0)
FS_SUB   = figstyle.check_size(8.0)
FS_BODY  = figstyle.check_size(8.0)
FS_REV   = figstyle.check_size(8.0)
LINE     = 0.138   # baseline-to-baseline for 8 pt body lines, in inches
BOX_PAD  = 0.05    # corner rounding, taken inside each box

# Vertical layout (bottom-up)
# Heights
H_SM   = 0.48   # small boxes (start / final)
H_RND  = 0.92   # round boxes
H_RND3 = H_RND + LINE   # Round 3 carries a fourth body line (CH-52)
GAP    = 0.19   # vertical gap between boxes (for the arrow; its label sits beside it)

# Compute cy values from bottom up
def stacked_cy(*heights_and_gaps):
    """Return centre-y list for a stack of (height, gap) pairs from bottom up.

    heights_and_gaps: alternating heights and gaps, starting with a height.
    First box sits with its bottom at 0.1 (bottom margin).
    """
    positions = []
    y = 0.1
    for i, val in enumerate(heights_and_gaps):
        if i % 2 == 0:  # it's a height
            cy = y + val / 2
            positions.append((cy, val))
            y += val
        else:            # it's a gap
            y += val
    return positions


layout = stacked_cy(
    H_SM,  GAP,
    H_RND, GAP,
    H_RND3, GAP,
    H_RND, GAP,
    H_RND, GAP,
    H_SM,
)

# Unpack: layout[0] = Final, …, layout[5] = Start node
cy_final, cy_r4, cy_r3, cy_r2, cy_r1, cy_start = [p[0] for p in layout]


# ── Helper functions ───────────────────────────────────────────────────────────

def draw_box(ax, cx, cy, width, height,
             title, subtitle, lines,
             face, border, title_color):
    """Draw a rounded box with title, optional subtitle, rule, and body lines.
    The rounding pad is taken inside the box, so its visible edge is the
    nominal width and height and the gaps between boxes stay as set."""
    rect = FancyBboxPatch(
        (cx - width / 2 + BOX_PAD, cy - height / 2 + BOX_PAD),
        width - 2 * BOX_PAD, height - 2 * BOX_PAD,
        boxstyle=f'round,pad={BOX_PAD}',
        facecolor=face, edgecolor=border,
        linewidth=1.5, zorder=3,
    )
    ax.add_patch(rect)

    y = cy + height / 2 - 0.08  # start just inside the top edge

    ax.text(cx, y, title,
            ha='center', va='top', fontsize=FS_TITLE,
            fontweight='bold', color=title_color, zorder=4)
    y -= 0.165

    if subtitle:
        ax.text(cx, y, subtitle,
                ha='center', va='top', fontsize=FS_SUB,
                color=C_SUB, style='italic', zorder=4)
        y -= 0.16

    # Thin divider line
    pad = 0.25
    ax.plot([cx - width / 2 + pad, cx + width / 2 - pad],
            [y, y],
            color='#CCCCCC', lw=0.8, zorder=4)
    y -= 0.055

    for line in lines:
        ax.text(cx, y, line,
                ha='center', va='top', fontsize=FS_BODY,
                color=C_TEXT, zorder=4)
        y -= LINE


def draw_arrow(ax, x, y_from, y_to, rev_label=None):
    """Draw a downward arrow; optionally place a centred revision label."""
    ax.annotate(
        '',
        xy=(x, y_to), xytext=(x, y_from),
        arrowprops=dict(
            arrowstyle='->', color=C_ARROW,
            lw=1.4, mutation_scale=12,
        ),
        zorder=2,
    )
    if rev_label:
        # Beside the arrow rather than on it, so the short arrow stays visible.
        mid = (y_from + y_to) / 2
        ax.text(x + 0.12, mid, rev_label,
                ha='left', va='center', fontsize=FS_REV,
                color=C_REV, style='italic', zorder=4)


# ── Build figure ───────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(FIG_W, FIG_H))
ax = fig.add_axes([0, 0, 1, 1])   # the axes fill the canvas: one data unit is one inch
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis('off')
fig.patch.set_facecolor('white')

# Fail loudly if the stack ever outgrows the canvas.
_top = layout[-1][0] + layout[-1][1] / 2
assert _top < FIG_H - 0.05, f'stack top {_top:.2f} exceeds canvas (FIG_H={FIG_H})'

# ── Boxes ──────────────────────────────────────────────────────────────────────

draw_box(ax, CX, cy_start, BOX_W_SM, H_SM,
         title='LLM-assisted systematic literature review',
         subtitle=None,
         # NOT "generated via thematic synthesis": the eight themes were
         # synthesized after the statement set was fixed. See Methods.
         lines=['17 candidate statements drafted from review items and study-team expertise'],
         face=C_START, border=C_BSTART, title_color=C_TSTART)

draw_box(ax, CX, cy_r1, BOX_W, H_RND,
         title='Round 1: Internal feedback',
         subtitle='16 December 2025 – 6 February 2026  │  N = 6',
         lines=[
             '17 statements + 1 ranking task + 5 open-ended questions',
             'infoXpand consortium members',
             'Written feedback: clarity, relevance, completeness, redundancy',
         ],
         face=C_ROUND, border=C_BROUND, title_color=C_TROUND)

draw_box(ax, CX, cy_r2, BOX_W, H_RND,
         title='Round 2: External feedback',
         subtitle='20 February – 13 March 2026  │  N = 5 of 10 invited',
         lines=[
             '26 statements + 1 ranking task + 7 open-ended questions',
             'Free-text feedback per statement',
             'Individual responses kept anonymous',
         ],
         face=C_ROUND, border=C_BROUND, title_color=C_TROUND)

draw_box(ax, CX, cy_r3, BOX_W, H_RND3,
         title='Round 3: First rating',
         subtitle='30 March – 20 April 2026  │  N = 18 of 38 invited',
         lines=[
             '42 statements + 3 ranking tasks + 7 open-ended questions',
             '6-point Likert ratings (1 = completely disagree, 6 = completely agree)',
             'Free-text comments per statement',
             'Ratings used to revise statements',
         ],
         face=C_ROUND, border=C_BROUND, title_color=C_TROUND)

draw_box(ax, CX, cy_r4, BOX_W, H_RND,
         title='Round 4: Final rating',
         subtitle='4 – 22 May 2026  │  N = 41 complete',
         lines=[
             '40 statements + 3 ranking tasks + 7 open-ended questions',
             'Contributors + external experts',
             '6-point Likert ratings + free-text feedback per section',
         ],
         face=C_ROUND, border=C_BROUND, title_color=C_TROUND)

draw_box(ax, CX, cy_final, BOX_W_SM, H_SM,
         title='Final consensus statements',
         subtitle=None,
         lines=['Consensus: IQR ≤ 1  │  Near-consensus: IQR ≤ 1.5'],
         face=C_FINAL, border=C_BFINAL, title_color=C_TFINAL)

# ── Arrows ─────────────────────────────────────────────────────────────────────

transitions = [
    (cy_start, H_SM,  cy_r1,   H_RND, None),
    (cy_r1,    H_RND, cy_r2,   H_RND, '17 → 26 statements'),
    (cy_r2,    H_RND, cy_r3,   H_RND3, '26 → 42 statements'),
    (cy_r3,    H_RND3, cy_r4,  H_RND, 'Revised and consolidated'),
    (cy_r4,    H_RND, cy_final, H_SM, None),
]

for (src_cy, src_h, dst_cy, dst_h, label) in transitions:
    y_from = src_cy - src_h / 2 - 0.03
    y_to   = dst_cy + dst_h / 2 + 0.03
    draw_arrow(ax, CX, y_from, y_to, rev_label=label)

# ── Save ───────────────────────────────────────────────────────────────────────

for out_dir in OUT_DIRS:
    os.makedirs(os.path.abspath(out_dir), exist_ok=True)
    pdf_path = os.path.join(out_dir, OUT_NAME + '.pdf')
    png_path = os.path.join(out_dir, OUT_NAME + '.png')
    # No tight bounding box: the file keeps its print size. CreationDate=None
    # keeps the PDF byte-identical between runs on unchanged input.
    fig.savefig(pdf_path, format='pdf', metadata={'CreationDate': None})
    # PNG sibling for the Word export (pandoc cannot embed PDF in docx).
    fig.savefig(png_path, format='png', dpi=200)
    print(f'Saved: {os.path.abspath(pdf_path)}')
    print(f'Saved: {os.path.abspath(png_path)}')
plt.close(fig)
