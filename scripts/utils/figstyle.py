"""Shared figure style for the Communications Health figures (CH-41).

Arial, with Helvetica as the fallback, at 8 pt, and TrueType fonts embedded in
the PDF (pdf.fonttype 42) so the text stays text. Every script that draws a
manuscript figure calls apply() before drawing. Explicit font sizes in those
scripts stay between MIN_SIZE and MAX_SIZE.

Figures are drawn at print size, at most MAX_WIDTH_IN wide. Those that fit the
manuscript's text block are drawn at TEXT_WIDTH_IN, its width, and included in
LaTeX at natural size, so the lettering prints at the size it was set.
"""
import matplotlib
from matplotlib import font_manager

BASE_SIZE = 8.0                 # pt
MIN_SIZE, MAX_SIZE = 8.0, 10.0  # bounds for explicit sizes
MAX_WIDTH_IN = 180 / 25.4       # the journal's widest figure, 180 mm
TEXT_WIDTH_IN = 390 / 72.27     # the manuscript's text block, 390 pt (137.6 mm)
TEXT_HEIGHT_IN = 548.5 / 72.27  # and its height, 548.5 pt (193.5 mm)
FAMILY = ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"]


def apply() -> None:
    matplotlib.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": FAMILY,
        "font.size": BASE_SIZE,
        "axes.titlesize": BASE_SIZE,
        "axes.labelsize": BASE_SIZE,
        "xtick.labelsize": BASE_SIZE,
        "ytick.labelsize": BASE_SIZE,
        "legend.fontsize": BASE_SIZE,
        "legend.title_fontsize": BASE_SIZE,
        "figure.titlesize": BASE_SIZE,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial",
        "mathtext.it": "Arial:italic",
        "mathtext.bf": "Arial:bold",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def font_file() -> str:
    """The file matplotlib uses for the first family it finds."""
    return font_manager.findfont(font_manager.FontProperties(family=FAMILY))


def check_size(size: float) -> float:
    """An explicit font size, refused outside MIN_SIZE to MAX_SIZE."""
    if not MIN_SIZE <= size <= MAX_SIZE:
        raise ValueError(f"font size {size} pt is outside {MIN_SIZE} to {MAX_SIZE} pt")
    return size
