"""Figure 1.2: Price gap S_i and return R_i around a tender offer (diagram, no data).

Drawn after the style of Suzuki (2015, Figure 1): time on the horizontal axis with the announcement date,
the return start date and the initial offer end date marked; the share price before the announcement and up to the
return start date as horizontal segments, then a line rising to the offer price by the initial offer end
date (the usual case for a full offer); version chosen by the author on 2026-11-12; the
offer price as a dotted line; vertical arrows naming the offer premium (offer price over the close on the day before the announcement,
the same as offer_premium_ratio in 01_compute_price_gap.py), the price gap S_i and the return R_i.

Output  output/figures/figure1_2_price_gap_diagram.png
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402

ANNOUNCE, START, END = 2.0, 3.2, 8.0
BEFORE, AFTER, OFFER = 1.0, 2.6, 3.3


def main():
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    ax.annotate("", xy=(0.3, 4.05), xytext=(0.3, 0.3), arrowprops=dict(arrowstyle="-|>", lw=1.2))
    ax.annotate("", xy=(9.9, 0.3), xytext=(0.3, 0.3), arrowprops=dict(arrowstyle="-|>", lw=1.2))
    ax.text(0.4, 4.05, "株価", va="top", fontsize=11)
    ax.text(9.9, 0.15, "時間", ha="right", va="top", fontsize=11)

    ax.plot([1.0, 9.3], [OFFER, OFFER], ls=":", color="black", lw=1.2)
    ax.text(9.35, OFFER, "買付価格", va="center", fontsize=11)
    ax.plot([0.3, ANNOUNCE], [BEFORE, BEFORE], color="black", lw=1.6)
    ax.plot([ANNOUNCE, ANNOUNCE], [BEFORE, AFTER], color="black", lw=1.6)
    ax.plot([ANNOUNCE, START], [AFTER, AFTER], color="black", lw=1.6)
    ax.plot([START, END], [AFTER, OFFER - 0.03], color="black", lw=1.6)

    ax.annotate("", xy=(1.7, OFFER), xytext=(1.7, BEFORE), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(1.6, (OFFER + BEFORE) / 2, "買付\nプレミアム", ha="right", va="center", fontsize=11, linespacing=1.4)
    ax.annotate("", xy=(START, OFFER), xytext=(START, AFTER), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(START - 0.1, (OFFER + AFTER) / 2, "価格差 $S_i$", ha="right", va="center", fontsize=11,
            bbox=dict(facecolor="white", edgecolor="none", pad=1))
    ax.plot([START, END], [AFTER, AFTER], ls="--", color="0.5", lw=0.8)
    ax.annotate("", xy=(END, OFFER - 0.03), xytext=(END, AFTER), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(END + 0.1, (OFFER + AFTER) / 2, "収益率 $R_i$", ha="left", va="center", fontsize=11)

    for x, label in [(ANNOUNCE, "公表日"), (START, "計算開始日"), (END, "当初の\n買付期間末日")]:
        ax.plot([x, x], [0.3, 0.42], color="black", lw=1.0)
        ax.text(x, 0.2, label, ha="center", va="top", fontsize=11)
    ax.annotate("", xy=(END, 0.62), xytext=(START, 0.62), arrowprops=dict(arrowstyle="<->", color="0.4", lw=0.8))
    ax.text((START + END) / 2, 0.68, "収益率を測る期間", ha="center", va="bottom", fontsize=10, color="0.3")
    fig.savefig(OUTPUT_FIGURES / "figure1_2_price_gap_diagram.png")


if __name__ == "__main__":
    main()
