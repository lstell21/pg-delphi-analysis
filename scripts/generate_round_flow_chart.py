#!/usr/bin/env python3
"""
Generate the Delphi participant-flow chart.

Companion to generate_delphi_flowchart.py, which shows the study procedure.
This one shows the panel flow: invited, responded (split into retained from an
earlier round and first-time respondents), and analyzed, for each round.

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

# Canvas holds the diagram only: 4 boxes + 3 gaps + thin margins.
FIG_W, FIG_H = 7.2, 8.95

CX       = 2.75   # centre of the round boxes (spine)
BOX_W    = 4.5    # round box width
SIDE_CX  = 6.05   # centre of the right-hand non-response notes
SIDE_W   = 1.75

# Colors
C_QUAL   = '#EBF5EB'   # pale green - qualitative rounds
C_QUANT  = '#D6EAF8'   # pale blue  - quantitative rounds
C_SIDE   = '#F4F6F6'   # pale grey  - non-response notes
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
FS_TITLE = 9.5
FS_SUB   = 8.0
FS_BODY  = 8.0
FS_REV   = 7.5
FS_SIDE  = 7.5
FS_NOTE  = 7.0

H_RND = 1.62    # round box height
GAP   = 0.62    # gap between boxes, leaves room for the arrow label


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

ROUNDS = [
    dict(title='Round 1: Internal feedback',
         subtitle='Core research team',
         invited='Invited 6',
         responded='Responded 6 (100%)',
         split='First-time respondents 6',
         analyzed='Analysed 6',
         nonresp=None,
         quant=False),
    dict(title='Round 2: External feedback',
         subtitle='Qualitative round',
         invited='Invited 10',
         responded='Responded 5 (50%)',
         split='Retained 0  ·  first-time 5',
         analyzed='Analysed 5',
         nonresp='Did not respond\n5',
         quant=False),
    dict(title='Round 3: First rating',
         subtitle='Quantitative round',
         invited='Invited 38',
         responded='Responded 18 (47%)',
         split='Retained 6  ·  first-time 12',
         analyzed='Analysed 18',
         nonresp='Did not respond\n20',
         quant=True),
    dict(title='Round 4: Final rating',
         subtitle='Quantitative round, definitive',
         invited='Invited 62 directly, survey shareable',
         responded='Responded 41 complete',
         split='Retention not determinable',
         analyzed='Analysed 43 to 51 per statement',
         nonresp='Denominator\nnot fixed',
         quant=True),
]

# Labels on the arrows between rounds: what carries over, and why.
TRANSITIONS = [
    'Core team not invited to Round 2',
    'All 5 retained, plus 1 returning from Round 1',
    'Anonymous survey: responses cannot be linked',
]

# No title, subtitle, or footnote block is drawn: the LaTeX \caption carries all
# of that. Keep it that way, and keep the caption in step with these numbers.


# ── Helpers ────────────────────────────────────────────────────────────────────

def draw_round(ax, cy, r):
    """Draw one round box: title, subtitle, divider, then the flow lines."""
    face   = C_QUANT if r['quant'] else C_QUAL
    border = C_BQUANT if r['quant'] else C_BQUAL
    tcol   = C_TQUANT if r['quant'] else C_TQUAL

    ax.add_patch(FancyBboxPatch(
        (CX - BOX_W / 2, cy - H_RND / 2), BOX_W, H_RND,
        boxstyle='round,pad=0.07',
        facecolor=face, edgecolor=border, linewidth=1.5, zorder=3,
    ))

    y = cy + H_RND / 2 - 0.13
    ax.text(CX, y, r['title'], ha='center', va='top',
            fontsize=FS_TITLE, fontweight='bold', color=tcol, zorder=4)
    y -= 0.22
    ax.text(CX, y, r['subtitle'], ha='center', va='top',
            fontsize=FS_SUB, color=C_SUB, style='italic', zorder=4)
    y -= 0.20

    pad = 0.25
    ax.plot([CX - BOX_W / 2 + pad, CX + BOX_W / 2 - pad], [y + 0.04] * 2,
            color='#CCCCCC', lw=0.8, zorder=4)
    y -= 0.15

    for key in ('invited', 'responded', 'split', 'analyzed'):
        text = r[key]
        # Grey out the cell we genuinely cannot fill.
        color = C_ND if text.startswith('Retention not') else C_TEXT
        weight = 'bold' if key == 'responded' else 'normal'
        ax.text(CX, y, text, ha='center', va='top', fontsize=FS_BODY,
                color=color, fontweight=weight, zorder=4)
        y -= 0.20


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
                bbox=dict(facecolor='white', edgecolor='none', pad=1.5))


# ── Build figure ───────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis('off')
fig.patch.set_facecolor('white')

BOTTOM = 0.30
cys = stacked_cy(H_RND, GAP, len(ROUNDS), BOTTOM)[::-1]  # top-down order

for cy, r in zip(cys, ROUNDS):
    draw_round(ax, cy, r)
    if r['nonresp']:
        draw_side(ax, cy, r['nonresp'])

for i, label in enumerate(TRANSITIONS):
    draw_arrow(ax, cys[i] - H_RND / 2 - 0.03, cys[i + 1] + H_RND / 2 + 0.03, label)

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
