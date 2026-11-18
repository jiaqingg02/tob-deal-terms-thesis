"""Figure 4.1: The positive part of the price gap, max(S_i, 0), and the price gap vs. the return (403 deals).

(a) Schematic (no data): how max(S_i, 0) is taken from the price gap S_i.
    A negative gap is set to 0; a positive gap is used as it is.
(b) Price gap S_i at the return start date vs. return R_i, for full and partial
    offers. Both axes are truncated at -30% and 60%; values outside are drawn
    on the edge. The dashed line is R_i = S_i (the stock price on the initial
    end date equals the offer price); the thick line is max(S_i, 0).
"""
import numpy as np
import matplotlib.pyplot as plt

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from sample import load_sample  # noqa: E402
from figure_style import MINUS  # noqa: E402

LO, HI = -30.0, 60.0
GROUPS = [  # (term_partial_tender_offer, label, marker)
    (0, "全部買付け", dict(marker="o", facecolors="none", edgecolors="0.45", s=18, linewidths=0.8)),
    (1, "部分買付け", dict(marker="x", color="0.25", s=26, linewidths=0.9)),
]
TICKS = [-30, 0, 20, 40, 60]
LABELS = [f"{MINUS}30以下", "0", "20", "40", "60以上"]
MAX_LINE = dict(color="black", lw=2.6, solid_capstyle="butt", zorder=3)


def panel_schematic(ax):
    """(a) max(S_i, 0): 0 for a negative gap, S_i for a positive gap."""
    ax.axhline(0, color="0.85", lw=0.6, zorder=0)
    ax.axvline(0, color="0.85", lw=0.6, zorder=0)
    ax.axvspan(LO, 0, color="0.93", zorder=0)
    ax.plot([LO, HI], [LO, HI], ls="--", color="0.6", lw=0.9, zorder=1)
    ax.plot([LO, 0], [0, 0], **MAX_LINE)
    ax.plot([0, HI], [0, HI], **MAX_LINE)
    ax.text(42, 55, r"$\max(S_i,0)$", ha="right", fontsize=11)
    # examples
    for s in (-15, 25):
        v = max(s, 0)
        ax.plot([s, s], [s, v], ls=":", color="black", lw=0.9, zorder=2)
        ax.plot(s, v, "o", color="black", ms=4.5, zorder=4)
    ax.annotate(f"$S_i={MINUS}15$ → 0", xy=(-15, 0), xytext=(-29, 12), fontsize=9.5,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3"))
    ax.annotate(r"$S_i=25$ → 25", xy=(25, 25), xytext=(28, 8), fontsize=9.5,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3"))
    ax.text(-15, -21, "株価が買付価格を\n上回る：0とする", ha="center", fontsize=9.5, linespacing=1.3)
    ax.text(30, -21, "株価が買付価格を\n下回る：$S_i$のまま", ha="center", fontsize=9.5, linespacing=1.3)
    ax.set_ylabel(r"価格差の正の部分 $\max(S_i,0)$（%）")
    ax.set_title("(a) 価格差の正の部分の取り方", fontsize=10.5)


def panel_data(ax, df):
    """(b) S_i vs. R_i with the line max(S_i, 0)."""
    ax.axhline(0, color="0.85", lw=0.6, zorder=0)
    ax.axvline(0, color="0.85", lw=0.6, zorder=0)
    ax.plot([LO, HI], [LO, HI], ls="--", color="0.6", lw=0.9, zorder=1)
    ax.plot([LO, 0], [0, 0], **{**MAX_LINE, "lw": 1.6, "zorder": 1.5})
    ax.plot([0, HI], [0, HI], **{**MAX_LINE, "lw": 1.6, "zorder": 1.5})
    ax.text(42, 55, r"$\max(S_i,0)$", ha="right", fontsize=11)
    for partial, label, marker in GROUPS:
        sub = df[df["term_partial_tender_offer"] == partial]
        ax.scatter(np.clip(sub["price_gap_at_start_pct"], LO, HI), np.clip(sub["return_to_initial_end_pct"], LO, HI),
                   label=f"{label}（{len(sub)}件）", zorder=2, **marker)
    ax.set_ylabel(r"収益率 $R_i$（%）")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_title("(b) 価格差と収益率の関係（403件）", fontsize=10.5)


def main():
    df = load_sample()
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(8.8, 4.5))
    panel_schematic(ax_a)
    panel_data(ax_b, df)
    for ax in (ax_a, ax_b):
        ax.set_xticks(TICKS, LABELS)
        ax.set_yticks(TICKS, LABELS)
        ax.set_xlim(LO - 3, HI + 3)
        ax.set_ylim(LO - 3, HI + 3)
        ax.set_xlabel(r"計算開始日の価格差 $S_i$（%）")
    fig.tight_layout(w_pad=2)
    fig.savefig(OUTPUT_FIGURES / "figure4_1_price_gap_and_return.png")


if __name__ == "__main__":
    main()
