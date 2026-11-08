"""Common matplotlib style for all figures (monochrome, Mincho font, 300 dpi)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({
    "font.family": "Hiragino Mincho ProN",
    "mathtext.fontset": "stix",
    "axes.unicode_minus": False,
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

BAR_COLOR = "0.45"
MINUS = "−"


def fmt_tick(v: float) -> str:
    """Integer tick label with a typographic minus sign."""
    return f"{MINUS}{abs(int(v))}" if v < 0 else f"{int(v)}"
