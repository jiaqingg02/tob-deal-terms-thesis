"""Figure 3.1: Distribution of the return R_i and the price gap S_i (403 deals).

Histogram with 2.5%-wide bins centred on 0. Values at or below -30% and at or
above 60% are pooled into the end bins.
"""
import numpy as np
import matplotlib.pyplot as plt

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
from sample import load_sample  # noqa: E402
from figure_style import BAR_COLOR, MINUS, fmt_tick  # noqa: E402

WIDTH, LO, HI = 2.5, -30.0, 60.0


def binned_counts(x):
    x = np.clip(x, LO, HI)
    centres = np.arange(LO, HI + WIDTH / 2, WIDTH)
    idx = np.rint((x - LO) / WIDTH).astype(int)
    return centres, np.bincount(idx, minlength=len(centres))


def main():
    df = load_sample()
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.0), sharey=True)
    panels = [("return_to_initial_end_pct", r"(a) 収益率 $R_i$（%）"), ("price_gap_at_start_pct", r"(b) 価格差 $S_i$（%）")]
    ticks = np.arange(-30, 61, 15)
    labels = [f"{MINUS}30以下"] + [fmt_tick(t) for t in ticks[1:-1]] + ["60以上"]
    for ax, (col, xlabel) in zip(axes, panels):
        centres, counts = binned_counts(df[col].to_numpy())
        ax.bar(centres, counts, width=WIDTH * 0.92, color=BAR_COLOR)
        ax.set_xticks(ticks, labels, fontsize=9)
        ax.set_xlabel(xlabel)
    axes[0].set_ylabel("件数")
    fig.savefig(OUTPUT_FIGURES / "figure3_1_return_and_price_gap_distribution.png")


if __name__ == "__main__":
    main()
