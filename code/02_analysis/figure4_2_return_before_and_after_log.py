"""Figure 4.2: Distribution of the return R_i and of y_i = 100 x ln(1 + R_i / 100) (403 deals).

Both panels use the same 5%-wide bins and the full range of the data (no pooling of
the tails), so that the effect of the log transformation on the large returns is visible.
The skewness of each distribution is printed.
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
from sample import load_sample  # noqa: E402
from figure_style import BAR_COLOR, fmt_tick  # noqa: E402

WIDTH = 5.0


def main():
    df = load_sample()
    r = df["return_to_initial_end_pct"].to_numpy()
    y = 100 * np.log1p(r / 100)
    lo = WIDTH * np.floor(min(r.min(), y.min()) / WIDTH)
    hi = WIDTH * np.ceil(max(r.max(), y.max()) / WIDTH)
    edges = np.arange(lo, hi + WIDTH / 2, WIDTH)
    for name, x in [("R", r), ("y", y)]:
        print(f"{name}: min {x.min():.2f}  max {x.max():.2f}  skewness {stats.skew(x):.2f}")

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.0), sharey=True, sharex=True)
    panels = [(r, r"(a) 収益率 $R_i$（%）"), (y, r"(b) 変換後の $y_i=100\ln(1+R_i/100)$")]
    for ax, (x, xlabel) in zip(axes, panels):
        ax.hist(x, bins=edges, color=BAR_COLOR, rwidth=0.92)
        ticks = np.arange(0, hi + 1, 50)
        ax.set_xticks(ticks, [fmt_tick(t) for t in ticks], fontsize=9)
        ax.set_xlim(lo, hi)
        ax.set_xlabel(xlabel)
    axes[0].set_ylabel("件数")
    fig.savefig(OUTPUT_FIGURES / "figure4_2_return_before_and_after_log.png")


if __name__ == "__main__":
    main()
