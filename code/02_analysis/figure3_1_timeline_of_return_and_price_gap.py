"""Figure 3.1: What R_i (eq. 3.1) and S_i (eq. 3.2) measure, on one deal's timeline.

Schematic only (no data). Shows J_i, the calculation start date J_i+1, the
initial end date E_i of the tender period, and an extension that is NOT used.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: E402,F401  (sets fonts)

X_ANN, X_J, X_J1, X_E, X_EXT = 0.9, 2.6, 4.8, 9.2, 11.1
Y_PRE, Y_J1, Y_E, Y_B = 1.9, 3.3, 4.4, 5.1
Y_AXIS = 0.0


def arrow(ax, x0, y0, x1, y1, style="<->", color="black", lw=1.0, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=10, color=color, lw=lw, ls=ls))


def main():
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(-1.6, 5.7)
    ax.axis("off")

    # time axis
    arrow(ax, 0.2, Y_AXIS, 12.2, Y_AXIS, style="->")
    ax.text(12.25, Y_AXIS, "時間", va="center", ha="left")
    ticks = [(X_ANN, "公表日"), (X_J, "$J_i$\n公表後最初の\n取引日"),
             (X_J1, "$J_i+1$\n計算開始日"), (X_E, "$E_i$\n当初の\n買付期間末日")]
    for x, lab in ticks:
        ax.plot([x, x], [Y_AXIS - 0.12, Y_AXIS + 0.12], color="black", lw=1)
        ax.text(x, Y_AXIS - 0.25, lab, ha="center", va="top", fontsize=10,
                linespacing=1.15)
    ax.plot([X_EXT, X_EXT], [Y_AXIS - 0.12, Y_AXIS + 0.12], color="0.55", lw=1)
    ax.text(X_EXT, Y_AXIS - 0.25, "延長後の末日\n（用いない）", ha="center",
            va="top", fontsize=10, color="0.45", linespacing=1.15)

    # observation period
    arrow(ax, X_J1, 0.55, X_E, 0.55, color="0.35")
    ax.text((X_J1 + X_E) / 2, 0.68, "観察期間（$R_i$ を計算する期間）",
            ha="center", va="bottom", fontsize=10, color="0.25")

    # price path
    ax.plot([0.3, X_J], [Y_PRE, Y_PRE], color="black", lw=2)
    ax.plot([X_J, X_J, X_J1], [Y_PRE, Y_J1, Y_J1], color="black", lw=2)
    ax.plot([X_J1, X_E], [Y_J1, Y_E], color="black", lw=2)
    ax.plot([X_E, X_EXT], [Y_E, Y_E + 0.35], color="0.6", lw=2, ls=(0, (4, 3)))

    # offer price
    ax.plot([0.3, X_EXT + 0.3], [Y_B, Y_B], color="black", lw=1, ls=":")
    ax.text(X_EXT + 0.4, Y_B, "$B_i/f_i$\n（買付価格）", va="center", ha="left",
            fontsize=10, linespacing=1.15)

    # reference level and points
    ax.plot([X_J1, X_E], [Y_J1, Y_J1], color="0.55", lw=0.8, ls="--")
    for x, y, lab, dy in [(X_J1, Y_J1, "$P_{i,J_i+1}$", -0.38),
                          (X_E, Y_E, "$P_{i,E_i}$", 0.38)]:
        ax.plot(x, y, "o", color="black", ms=5)
        ax.text(x, y + dy, lab, ha="center", va="center", fontsize=11)

    # S_i bracket at J_i+1
    arrow(ax, X_J1 + 0.25, Y_J1 + 0.05, X_J1 + 0.25, Y_B - 0.05)
    ax.text(X_J1 + 0.4, (Y_J1 + Y_B) / 2, "価格差 $S_i$（式3.2）",
            va="center", ha="left", fontsize=10.5)
    # R_i bracket at E_i
    arrow(ax, X_E + 0.3, Y_J1 + 0.05, X_E + 0.3, Y_E - 0.05)
    ax.text(X_E + 0.45, (Y_J1 + Y_E) / 2, "収益率 $R_i$（式3.1）",
            va="center", ha="left", fontsize=10.5)

    OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FIGURES / "figure3_1_timeline_of_return_and_price_gap.png")


if __name__ == "__main__":
    main()
