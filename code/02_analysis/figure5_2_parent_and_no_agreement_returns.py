"""Figure 5.2: Price gap S_i and return R_i, deals with and without (a) the parent-subsidiary listing term and
(b) the no-agreement-with-shareholders term (403 deals).

Filled black points: deals with the term; hollow grey circles: the other deals. The dashed line is R_i = S_i,
i.e. the stock price at the initial offer end equals the offer price. Both axes are truncated at -30% and 60%;
values outside are drawn on the edge.

Also writes output/tables/figure5_2_returns_relative_to_price_gap.csv: for each term, the share of deals with and
without the term whose return is within PINNED_THRESHOLD_PCT points of the price gap (|R_i - S_i| <= 1, the price
stayed at the offer price) and the share whose return exceeds the price gap by more than that (R_i - S_i > 1,
the price rose above the offer price). These shares are quoted in Section 5.1.2.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_FIGURES, OUTPUT_TABLES, PINNED_THRESHOLD_PCT  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from figure_style import MINUS  # noqa: E402
from sample import load_sample  # noqa: E402

LO, HI = -30.0, 60.0
TERMS = [("term_resolves_parent_subsidiary_listing", "(a) 親子上場の解消"),
         ("term_no_tender_or_non_tender_agreement_with_shareholders", "(b) 株主との応募・不応募の合意の記載なし")]


def main():
    df = load_sample()
    gap, ret = df["price_gap_at_start_pct"], df["return_to_initial_end_pct"]
    difference = ret - gap
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    ticks = [-30, 0, 20, 40, 60]
    labels = [f"{MINUS}30以下", "0", "20", "40", "60以上"]
    rows = []
    for ax, (term, title) in zip(axes, TERMS):
        has = df[term] == 1
        ax.plot([LO, HI], [LO, HI], ls="--", color="0.45", lw=0.9, zorder=1)
        ax.scatter(np.clip(gap[~has], LO, HI), np.clip(ret[~has], LO, HI), s=16, facecolors="none",
                   edgecolors="0.55", linewidths=0.6, zorder=2, label=f"当たらない案件（{(~has).sum()}件）")
        ax.scatter(np.clip(gap[has], LO, HI), np.clip(ret[has], LO, HI), s=16, color="black", linewidths=0,
                   zorder=3, label=f"当たる案件（{has.sum()}件）")
        ax.set_xticks(ticks, labels)
        ax.set_yticks(ticks, labels)
        ax.set_xlim(LO - 3, HI + 3)
        ax.set_ylim(LO - 3, HI + 3)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("計算開始日の価格差（%）")
        ax.legend(loc="upper left", frameon=False, fontsize=9)
        for mask, group in [(has, "当たる案件"), (~has, "当たらない案件")]:
            rows.append({"取引条件": title[4:], "案件": group, "件数": int(mask.sum()),
                         "収益率が価格差から1ポイント以内の割合": round((difference[mask].abs() <= PINNED_THRESHOLD_PCT).mean(), 2),
                         "収益率が価格差を1ポイント超えて上回る割合": round((difference[mask] > PINNED_THRESHOLD_PCT).mean(), 2)})
    axes[0].set_ylabel("収益率（%）")
    fig.savefig(OUTPUT_FIGURES / "figure5_2_parent_and_no_agreement_returns.png", bbox_inches="tight")
    table = pd.DataFrame(rows)
    table.to_csv(OUTPUT_TABLES / "figure5_2_returns_relative_to_price_gap.csv", index=False, encoding="utf-8-sig")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
