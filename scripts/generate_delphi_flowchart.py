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

# ── Output path ────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURES_DIR = os.path.join(SCRIPT_DIR, '..', 'figures')

# A second output target can be added to OUT_DIRS without other changes.
OUT_DIRS = [
    FIGURES_DIR,
]
OUT_NAME = 'delphi_flowchart'

# ── Design constants ───────────────────────────────────────────────────────────

FIG_W, FIG_H = 7.0, 10.6   # figure size in inches = data coordinate range
CX      = 3.5               # horizontal centre of all boxes
BOX_W   = 6.2               # box width
BOX_W_SM = 5.4              # width of smaller start/end boxes (must fit their text)

# Colors
C_START  = '#D6EAF8'   # pale blue  – starting node
C_ROUND  = '#EBF5EB'   # pale green – Delphi rounds
C_FINAL  = '#FEF9E7'   # pale amber – final output
C_BSTART = '#2471A3'   # blue border
C_BROUND = '#1E8449'   # green border
C_BFINAL = '#9A7D0A'   # amber border
C_TSTART = '#1A5276'   # blue title text
C_TROUND = '#1E8449'   # green title text
C_TFINAL = '#7D6608'   # amber title text
C_TEXT   = '#2C3E50'   # body text
C_SUB    = '#626567'   # subtitle text
C_ARROW  = '#566573'   # arrow colour
C_REV    = '#808B96'   # revision label text

# Typography
FS_TITLE = 9.5
FS_SUB   = 8.0
FS_BODY  = 8.0
FS_REV   = 7.5

# Vertical layout (bottom-up)
# Heights
H_SM   = 0.85   # small boxes (start / final)
H_RND  = 1.45   # round boxes
GAP    = 0.48   # vertical gap between boxes (for arrow + revision label)

# Compute cy values from bottom up
def stacked_cy(*heights_and_gaps):
    """Return centre-y list for a stack of (height, gap) pairs from bottom up.

    heights_and_gaps: alternating heights and gaps, starting with a height.
    First box sits with its bottom at 0.15 (bottom margin).
    """
    positions = []
    y = 0.35
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
    H_RND, GAP,
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
    """Draw a rounded box with title, optional subtitle, rule, and body lines."""
    rect = FancyBboxPatch(
        (cx - width / 2, cy - height / 2), width, height,
        boxstyle='round,pad=0.07',
        facecolor=face, edgecolor=border,
        linewidth=1.5, zorder=3,
    )
    ax.add_patch(rect)

    y = cy + height / 2 - 0.13  # start just inside the top edge

    ax.text(cx, y, title,
            ha='center', va='top', fontsize=FS_TITLE,
            fontweight='bold', color=title_color, zorder=4)
    y -= 0.22

    if subtitle:
        ax.text(cx, y, subtitle,
                ha='center', va='top', fontsize=FS_SUB,
                color=C_SUB, style='italic', zorder=4)
        y -= 0.20

    # Thin divider line
    pad = 0.25
    ax.plot([cx - width / 2 + pad, cx + width / 2 - pad],
            [y + 0.04, y + 0.04],
            color='#CCCCCC', lw=0.8, zorder=4)
    y -= 0.14

    for line in lines:
        ax.text(cx, y, line,
                ha='center', va='top', fontsize=FS_BODY,
                color=C_TEXT, zorder=4)
        y -= 0.195


def draw_arrow(ax, x, y_from, y_to, rev_label=None):
    """Draw a downward arrow; optionally place a centred revision label."""
    ax.annotate(
        '',
        xy=(x, y_to), xytext=(x, y_from),
        arrowprops=dict(
            arrowstyle='->', color=C_ARROW,
            lw=1.8, mutation_scale=15,
        ),
        zorder=2,
    )
    if rev_label:
        mid = (y_from + y_to) / 2
        ax.text(x, mid, rev_label,
                ha='center', va='center', fontsize=FS_REV,
                color=C_REV, style='italic', zorder=4,
                bbox=dict(facecolor='white', edgecolor='none', pad=1.5))


# ── Build figure ───────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis('off')
fig.patch.set_facecolor('white')

# ── Boxes ──────────────────────────────────────────────────────────────────────

draw_box(ax, CX, cy_start, BOX_W_SM, H_SM,
         title='Systematic Literature Review',
         subtitle=None,
         # NOT "generated via thematic synthesis": the eight themes were
         # synthesized after the statement set was fixed. See Methods.
         lines=['17 candidate statements drafted from review items and author expertise'],
         face=C_START, border=C_BSTART, title_color=C_TSTART)

draw_box(ax, CX, cy_r1, BOX_W, H_RND,
         title='Round 1: Internal feedback',
         subtitle='December 2025 – February 2026  │  N = 6',
         lines=[
             '17 statements + 1 ranking task + 5 open-ended questions',
             'Core research team review',
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

draw_box(ax, CX, cy_r3, BOX_W, H_RND,
         title='Round 3: First rating',
         subtitle='30 March – 20 April 2026  │  N = 18 of 38 invited',
         lines=[
             '42 statements + 3 ranking tasks + 7 open-ended questions',
             '6-point Likert ratings (1 = strongly disagree, 6 = strongly agree)',
             'Free-text comments per statement',
         ],
         face=C_ROUND, border=C_BROUND, title_color=C_TROUND)

draw_box(ax, CX, cy_r4, BOX_W, H_RND,
         title='Round 4: Final rating',
         subtitle='4 – 22 May 2026  │  N = 41 complete',
         lines=[
             '40 statements + 3 ranking tasks + 7 open-ended questions',
             'Core authors + panel members + external experts',
             '6-point Likert ratings + free-text feedback per section',
         ],
         face=C_ROUND, border=C_BROUND, title_color=C_TROUND)

draw_box(ax, CX, cy_final, BOX_W_SM, H_SM,
         title='Final consensus recommendations',
         subtitle=None,
         lines=['Consensus: IQR ≤ 1  │  Near-consensus: IQR ≤ 1.5'],
         face=C_FINAL, border=C_BFINAL, title_color=C_TFINAL)

# ── Arrows ─────────────────────────────────────────────────────────────────────

transitions = [
    (cy_start, H_SM,  cy_r1,   H_RND, None),
    (cy_r1,    H_RND, cy_r2,   H_RND, '17 → 26 statements'),
    (cy_r2,    H_RND, cy_r3,   H_RND, '26 → 42 statements'),
    (cy_r3,    H_RND, cy_r4,   H_RND, 'Revised and consolidated'),
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
    fig.savefig(pdf_path, format='pdf', bbox_inches='tight', pad_inches=0.12)
    # PNG sibling for the Word export (pandoc cannot embed PDF in docx).
    fig.savefig(png_path, format='png', dpi=200, bbox_inches='tight', pad_inches=0.12)
    print(f'Saved: {os.path.abspath(pdf_path)}')
    print(f'Saved: {os.path.abspath(png_path)}')
plt.close(fig)
