"""Figure 4.1: Price gap S_i at the return start date vs. return R_i, for full and partial offers (403 deals).

Both axes are truncated at -30% and 60%; values outside are drawn on the edge.
The dashed line is R_i = S_i (the stock price on the initial end date equals
the offer price).
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
    (0, "全部買付け", dict(marker="o", facecolors="none", edgecolors="0.3", s=18, linewidths=0.8)),
    (1, "部分買付け", dict(marker="x", color="black", s=26, linewidths=0.9)),
]


def main():
    df = load_sample()
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    ax.axhline(0, color="0.85", lw=0.6, zorder=0)
    ax.axvline(0, color="0.85", lw=0.6, zorder=0)
    ax.plot([LO, HI], [LO, HI], ls="--", color="0.45", lw=0.9, zorder=1)
    ax.text(45, 39, r"$R_i = S_i$", fontsize=11)

    for partial, label, marker in GROUPS:
        sub = df[df["term_partial_tender_offer"] == partial]
        ax.scatter(np.clip(sub["price_gap_at_start_pct"], LO, HI), np.clip(sub["return_to_initial_end_pct"], LO, HI),
                   label=f"{label}（{len(sub)}件）", zorder=2, **marker)

    ticks = [-30, 0, 20, 40, 60]
    labels = [f"{MINUS}30以下", "0", "20", "40", "60以上"]
    ax.set_xticks(ticks, labels)
    ax.set_yticks(ticks, labels)
    ax.set_xlim(LO - 3, HI + 3)
    ax.set_ylim(LO - 3, HI + 3)
    ax.set_xlabel(r"計算開始日の価格差 $S_i$（%）")
    ax.set_ylabel(r"収益率 $R_i$（%）")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.savefig(OUTPUT_FIGURES / "figure4_1_price_gap_and_return.png")


if __name__ == "__main__":
    main()
