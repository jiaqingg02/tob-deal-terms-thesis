"""Figure C.1 (Appendix C): Distribution of |S_i| for full tender offers (339 deals).

Shows where the threshold of the pinned dummy (config.PINNED_THRESHOLD_PCT = 1%) lies.

0.25%-wide bins, right-closed (so |S_i| = 1 falls in the 0.75-1 bin and is
classified as pinned, consistent with the |S_i| <= 1 rule). Values above 5%
are pooled into the last bin.
"""
import numpy as np
import matplotlib.pyplot as plt

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
from config import PINNED_THRESHOLD_PCT  # noqa: E402
from sample import load_sample  # noqa: E402
from figure_style import BAR_COLOR  # noqa: E402

WIDTH, TOP = 0.25, 5.0


def main():
    df = load_sample()
    full = df[df["term_partial_tender_offer"] == 0]
    a = full["price_gap_at_start_pct"].abs().to_numpy()
    assert len(full) == 339

    edges = np.arange(0, TOP + WIDTH / 2, WIDTH)
    # right-closed bins: (e_k, e_{k+1}], first bin includes 0
    idx = np.clip(np.ceil(a / WIDTH).astype(int) - 1, 0, None)
    idx = np.minimum(idx, len(edges) - 1)          # > 5% -> last (pooled) bin
    counts = np.bincount(idx, minlength=len(edges))
    print("|S|<=0.5:", int((a <= 0.5).sum()), " 0.5<|S|<=1:", int(((a > 0.5) & (a <= 1)).sum()))

    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    ax.bar(edges[:-1] + WIDTH / 2, counts[:-1], width=WIDTH * 0.97, color=BAR_COLOR)
    ax.bar(TOP + WIDTH / 2, counts[-1], width=WIDTH * 0.97, color=BAR_COLOR)
    ax.axvline(PINNED_THRESHOLD_PCT, color="black", ls="--", lw=1)
    ax.text(PINNED_THRESHOLD_PCT + 0.08, counts.max() * 0.9, "1%")
    ax.set_xticks([0, 1, 2, 3, 4, 5], ["0", "1", "2", "3", "4", "5以上"])
    ax.set_xlabel(r"全部買付けの計算開始日の価格差の絶対値 $|S_i|$（%）")
    ax.set_ylabel("件数")
    fig.savefig(OUTPUT_FIGURES / "figureC1_absolute_price_gap_distribution.png")


if __name__ == "__main__":
    main()
