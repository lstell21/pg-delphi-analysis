#!/usr/bin/env python3
"""
Generate the Delphi participant-flow chart.

Companion to generate_delphi_flowchart.py, which shows the study procedure.
This one shows the panel flow. Each round box carries the same four cells in
the same order, headed by the quantity they report: invited, responded with
the response rate, respondents split into those retained from an earlier round
and those responding for the first time, and analysed. A cell that cannot be
filled says so rather than staying blank.

The panel broadened deliberately between rounds rather than staying fixed, so
response rate and attrition are not the same thing. The layout keeps the two
apart: non-response branches right, retention flows down the spine.

Usage:
    python scripts/generate_round_flow_chart.py

Output:
    figures/round_flow.pdf  (+ .png sibling for the Word export)
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
OUT_NAME = 'round_flow'

# ── Design constants (shared with generate_delphi_flowchart.py) ────────────────

# Canvas holds the diagram only: 4 boxes + 3 gaps + thin margins, plus one
# footnote line under the last box.
FIG_W, FIG_H = 9.10, 10.60

CX       = 3.55   # centre of the round boxes (spine)
BOX_W    = 6.50   # round box width
SIDE_CX  = 8.10   # centre of the right-hand non-response notes
SIDE_W   = 1.80

# Colors
C_QUAL   = '#EBF5EB'   # pale green - qualitative rounds
C_QUANT  = '#D6EAF8'   # pale blue  - quantitative rounds
C_SIDE   = '#F4F6F6'   # pale grey  - non-response notes
C_CELL   = '#FFFFFF'   # inner cells sit white on the round's tint
C_CEDGE  = '#C8CFD4'   # inner cell border
C_RULE   = '#CCCCCC'
C_BQUAL  = '#1E8449'
C_BQUANT = '#2471A3'
C_BSIDE  = '#AEB6BF'
C_TQUAL  = '#1E8449'
C_TQUANT = '#1A5276'
C_TEXT   = '#2C3E50'
C_SUB    = '#626567'
C_ARROW  = '#566573'
C_REV    = '#808B96'
C_ND     = '#943126'   # not-determinable marker

# Typography
FS_TITLE = 10.5
FS_BADGE = 9.5
FS_SUB   = 8.5
FS_BODY  = 9.5
FS_LABEL = 7.8
FS_REV   = 8.0
FS_SIDE  = 8.0
FS_NOTE  = 7.2

H_RND  = 1.92   # round box height; the slack sits between rule and headings
H_CELL = 0.62   # inner cell height
GAP    = 0.78   # gap between boxes, so the arrow shows either side of its label

# Column headings, and the relative widths of the cells under them. The third
# cell is the only one that splits: retained above, first-time below.
COLUMNS = [
    ('Invited',                    0.72, 'invited'),
    ('Responded (%)',              1.16, 'responded'),
    ('First-time\nrespondents',    1.30, 'split'),
    ('Analysed',                   1.08, 'analysed'),
]


def stacked_cy(height, gap, n, bottom):
    """Centre-y for n equal boxes stacked upward from `bottom`."""
    out, y = [], bottom
    for _ in range(n):
        out.append(y + height / 2)
        y += height + gap
    return out


# ── Round data ─────────────────────────────────────────────────────────────────
# This block is the source of truth for the participant flow; it superseded
# tables/round_flow.tex. Numbers must agree with the Methods narrative.
# retained + first-time = responded, for every round where retention is known.
#
# Cell values are (main line, second line or None). A second line set in the
# not-determinable colour is how a cell reports what it cannot report. 'split'
# is either a (retained, first-time) pair or a single string filling the cell.

ROUNDS = [
    dict(number='Round 1',
         title='Internal feedback',
         subtitle='infoXpand consortium group',
         invited=('6', None),
         responded=('6 (100%)', None),
         split=('not applicable', '6'),
         analysed=('6', None),
         nonresp=None,
         quant=False),
    dict(number='Round 2',
         title='External feedback',
         subtitle='Qualitative round',
         invited=('10', None),
         responded=('5 (50%)', None),
         split=('0', '5'),
         analysed=('5', None),
         nonresp='Did not respond\n5',
         quant=False),
    dict(number='Round 3',
         title='First rating',
         subtitle='Quantitative round',
         invited=('38', None),
         responded=('18 (47%)', None),
         split=('6', '12'),
         analysed=('18', None),
         nonresp='Did not respond\n20',
         quant=True),
    dict(number='Round 4',
         title='Final rating',
         subtitle='Quantitative round',
         invited=('62*', None),
         responded=('41 complete', 'rate not determinable'),
         split='Retention not\ndeterminable',
         analysed=('43 to 51', 'per statement'),
         nonresp='Denominator\nnot fixed',
         quant=True),
]

# Labels on the arrows between rounds: what carries over, and why.
TRANSITIONS = [
    'Round 1 group not invited to Round 2',
    'All 5 retained, plus 1 returning from Round 1',
    'Anonymous survey: responses cannot be linked',
]

# The asterisk on Round 4's invited count, explained under the last box.
FOOTNOTE = '*Shareable survey link, so the number invited is not a fixed denominator'

# No title, subtitle, or footnote block is drawn beyond that one line: the
# LaTeX \caption carries the rest. Keep the caption in step with these numbers,
# and keep the four column headings and the caption's four terms identical.


# ── Helpers ────────────────────────────────────────────────────────────────────

def cell_xs():
    """Left edge and width of each of the four cells, across the box interior."""
    pad, gut = 0.16, 0.09
    inner = BOX_W - 2 * pad
    total = sum(w for _, w, _ in COLUMNS)
    unit = (inner - gut * (len(COLUMNS) - 1)) / total
    xs, x = [], CX - BOX_W / 2 + pad
    for _, w, _ in COLUMNS:
        xs.append((x, w * unit))
        x += w * unit + gut
    return xs


def draw_value(ax, x, cy, main, second, tcol):
    """One cell's value: the count, and under it the line that qualifies it."""
    if second is None:
        ax.text(x, cy, main, ha='center', va='center', fontsize=FS_BODY,
                fontweight='bold', color=tcol, zorder=5)
        return
    ax.text(x, cy + 0.07, main, ha='center', va='center', fontsize=FS_BODY,
            fontweight='bold', color=tcol, zorder=5)
    # Red marks a quantity we cannot report; a plain qualifier stays grey.
    scol = C_ND if 'not determinable' in second else C_SUB
    ax.text(x, cy - 0.11, second, ha='center', va='center',
            fontsize=FS_NOTE - 0.6, color=scol, style='italic', zorder=5)


def draw_split_cell(ax, x0, w, y0, h, split):
    """The third cell: retained above the rule, first-time below it."""
    if isinstance(split, str):
        ax.text(x0 + w / 2, y0 + h / 2, split, ha='center', va='center',
                fontsize=FS_NOTE, color=C_ND, style='italic', zorder=5,
                linespacing=1.4)
        return

    ax.plot([x0 + 0.08, x0 + w - 0.08], [y0 + h / 2] * 2,
            color=C_CEDGE, lw=0.8, zorder=5)
    rows = (('Retained', split[0], y0 + 3 * h / 4),
            ('First-time', split[1], y0 + h / 4))
    for label, value, y in rows:
        ax.text(x0 + 0.09, y, label, ha='left', va='center',
                fontsize=FS_LABEL, color=C_SUB, zorder=5)
        known = value.strip().isdigit()
        ax.text(x0 + w - 0.09, y, value, ha='right', va='center',
                fontsize=FS_BODY if known else FS_NOTE - 0.6,
                fontweight='bold' if known else 'normal',
                color=C_TEXT if known else C_SUB,
                style='normal' if known else 'italic', zorder=5)


def draw_round(ax, cy, r):
    """One round box: badge and heading, then the four cells under their heads."""
    face   = C_QUANT if r['quant'] else C_QUAL
    border = C_BQUANT if r['quant'] else C_BQUAL
    tcol   = C_TQUANT if r['quant'] else C_TQUAL

    ax.add_patch(FancyBboxPatch(
        (CX - BOX_W / 2, cy - H_RND / 2), BOX_W, H_RND,
        boxstyle='round,pad=0.07',
        facecolor=face, edgecolor=border, linewidth=1.5, zorder=3,
    ))

    # Round number as an outlined badge in the top-left corner.
    badge_w, badge_h = 0.95, 0.28
    badge_x = CX - BOX_W / 2 + 0.20
    badge_y = cy + H_RND / 2 - 0.14 - badge_h
    ax.add_patch(FancyBboxPatch(
        (badge_x, badge_y), badge_w, badge_h,
        boxstyle='round,pad=0.03',
        facecolor='none', edgecolor=border, linewidth=1.2, zorder=4,
    ))
    ax.text(badge_x + badge_w / 2, badge_y + badge_h / 2, r['number'],
            ha='center', va='center', fontsize=FS_BADGE, fontweight='bold',
            color=tcol, zorder=5)

    ax.text(CX, badge_y + badge_h / 2, r['title'], ha='center', va='center',
            fontsize=FS_TITLE, fontweight='bold', color=tcol, zorder=4)
    y = badge_y - 0.06
    ax.text(CX, y, r['subtitle'], ha='center', va='top',
            fontsize=FS_SUB, color=C_SUB, style='italic', zorder=4)
    y -= 0.20

    pad = 0.25
    ax.plot([CX - BOX_W / 2 + pad, CX + BOX_W / 2 - pad], [y] * 2,
            color=C_RULE, lw=0.8, zorder=4)

    # The four cells, headed by the quantity each reports.
    y0 = cy - H_RND / 2 + 0.13
    for (x0, w), (head, _, key) in zip(cell_xs(), COLUMNS):
        ax.text(x0 + w / 2, y0 + H_CELL + 0.05, head, ha='center', va='bottom',
                fontsize=FS_LABEL, color=C_SUB, zorder=4, linespacing=1.25)
        ax.add_patch(FancyBboxPatch(
            (x0, y0), w, H_CELL,
            boxstyle='round,pad=0.02',
            facecolor=C_CELL, edgecolor=C_CEDGE, linewidth=0.9, zorder=4,
        ))
        if key == 'split':
            draw_split_cell(ax, x0, w, y0, H_CELL, r['split'])
        else:
            draw_value(ax, x0 + w / 2, y0 + H_CELL / 2, *r[key], C_TEXT)


def draw_side(ax, cy, text):
    """Grey note to the right, with a short connector from the spine."""
    h = 0.52
    ax.add_patch(FancyBboxPatch(
        (SIDE_CX - SIDE_W / 2, cy - h / 2), SIDE_W, h,
        boxstyle='round,pad=0.05',
        facecolor=C_SIDE, edgecolor=C_BSIDE, linewidth=1.0, zorder=3,
    ))
    ax.text(SIDE_CX, cy, text, ha='center', va='center',
            fontsize=FS_SIDE, color=C_SUB, zorder=4, linespacing=1.35)
    ax.annotate('', xy=(SIDE_CX - SIDE_W / 2, cy), xytext=(CX + BOX_W / 2, cy),
                arrowprops=dict(arrowstyle='->', color=C_BSIDE, lw=1.2,
                                mutation_scale=11), zorder=2)


def draw_arrow(ax, y_from, y_to, label):
    ax.annotate('', xy=(CX, y_to), xytext=(CX, y_from),
                arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.8,
                                mutation_scale=15), zorder=2)
    if label:
        ax.text(CX, (y_from + y_to) / 2, label, ha='center', va='center',
                fontsize=FS_REV, color=C_REV, style='italic', zorder=4,
                bbox=dict(facecolor='white', edgecolor='none', pad=1.0))


# ── Build figure ───────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis('off')
fig.patch.set_facecolor('white')

BOTTOM = 0.45
cys = stacked_cy(H_RND, GAP, len(ROUNDS), BOTTOM)[::-1]  # top-down order

for cy, r in zip(cys, ROUNDS):
    draw_round(ax, cy, r)
    if r['nonresp']:
        draw_side(ax, cy, r['nonresp'])

for i, label in enumerate(TRANSITIONS):
    draw_arrow(ax, cys[i] - H_RND / 2 - 0.03, cys[i + 1] + H_RND / 2 + 0.03, label)

ax.text(CX - BOX_W / 2, BOTTOM - 0.26, FOOTNOTE, ha='left', va='center',
        fontsize=FS_NOTE, color=C_SUB, zorder=4)

# Fail loudly if the stack ever outgrows the canvas.
_top = cys[0] + H_RND / 2
assert _top < FIG_H, f'stack top {_top:.2f} exceeds canvas (FIG_H={FIG_H})'

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
