"""Figure 4.1: How the 403 deals are classified into three groups.

Box counts are computed from the data, not typed in by hand.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from sample import load_sample  # noqa: E402


def box(ax, x, y, w, h, text, shaded=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                fc="0.93" if shaded else "white", ec="black", lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=12, linespacing=1.6)


def arrow(ax, start, end, label=None, label_xy=None):
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="->", lw=1.2, color="black", mutation_scale=14))
    if label:
        ax.text(*label_xy, label, ha="left", va="center", fontsize=11)


def main():
    df = load_sample()
    n = len(df)
    n_part = int((df["deal_group"] == "partial").sum())
    n_full = n - n_part
    n_pin = int((df["deal_group"] == "pinned").sum())
    n_free = int((df["deal_group"] == "free").sum())

    fig, ax = plt.subplots(figsize=(11.0, 5.0))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5)
    ax.axis("off")

    box(ax, 0.3, 3.65, 1.8, 1.0, f"分析対象\n{n}件")
    box(ax, 2.7, 3.6, 3.5, 1.1, "買付予定数に上限がある、\nまたは上場の維持を明記しているか", shaded=True)
    box(ax, 7.8, 3.7, 2.7, 0.9, f"部分買付け\n{n_part}件")
    box(ax, 2.7, 1.0, 3.5, 1.1, "計算開始日の価格差が\n$|S_i| \\leq 1\\%$ か", shaded=True)
    box(ax, 7.8, 2.0, 2.7, 0.9, f"張り付いた全部買付け\n{n_pin}件")
    box(ax, 7.8, 0.45, 2.7, 0.9, f"自由に動く全部買付け\n{n_free}件")

    arrow(ax, (2.1, 4.15), (2.7, 4.15))
    arrow(ax, (6.2, 4.15), (7.8, 4.15), "はい", (6.85, 4.38))
    arrow(ax, (4.45, 3.6), (4.45, 2.1), f"いいえ（全部買付け {n_full}件）", (4.55, 2.85))
    arrow(ax, (6.2, 1.75), (7.8, 2.2), "はい", (6.8, 2.3))
    arrow(ax, (6.2, 1.25), (7.8, 0.9), "いいえ", (6.7, 0.85))

    fig.savefig(OUTPUT_FIGURES / "figure4_1_classification_of_deals.png")


if __name__ == "__main__":
    main()
