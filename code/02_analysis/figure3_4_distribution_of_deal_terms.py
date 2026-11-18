"""Figure 3.4: Distribution of the deal terms read from the two documents (403 deals).

(a) Share of deals for which each 0/1 deal term equals 1, in the order of
    Table 3.4. The funding term is missing for 64 deals without a funding
    table, so its share is out of the remaining 339 deals.
(b) Number of deal terms equal to 1 per deal (a missing funding term is
    counted as 0).
The counts are checked against Table 3.4 before drawing.
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
from sample import load_sample  # noqa: E402
from figure_style import BAR_COLOR  # noqa: E402

DEAL_TERMS = [
    ("term_partial_tender_offer", "部分買付け", 64),
    ("term_competitive_bidding", "入札・競合あり", 92),
    ("term_no_price_increase_confirmed_in_negotiation_with_target",
     "交渉による価格の引上げが確認されない", 95),
    ("term_investment_fund_involved_in_acquirer", "買付者へのファンドの関与", 96),
    ("term_management_buyout_without_fund", "MBO（ファンドの関与なし）", 62),
    ("term_no_tender_or_non_tender_agreement_with_shareholders",
     "株主との応募・不応募の合意の記載なし", 90),
    ("term_board_does_not_recommend_tender", "取締役会が応募を推奨しない", 78),
    ("term_pending_regulatory_approval", "許認可の承認待ち", 14),
    ("term_no_borrowing_or_equity_financing_planned",
     "買付資金に借入・出資の予定なし（339件中）", 126),
    ("term_abolishes_shareholder_benefits", "株主優待の廃止", 98),
    ("term_resolves_parent_subsidiary_listing", "親子上場の解消", 75),
]


def main():
    df = load_sample()
    columns = [c for c, _, _ in DEAL_TERMS]
    counts, shares = [], []
    for column, _, expected in DEAL_TERMS:
        values = df[column].dropna()
        count = int(values.sum())
        assert count == expected, (column, count, expected)
        counts.append(count)
        shares.append(100 * count / len(values))
    terms_per_deal = df[columns].fillna(0).sum(axis=1).astype(int).value_counts().sort_index()

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(9.4, 4.0),
                                     gridspec_kw={"width_ratios": [1.75, 1]})
    y = np.arange(len(DEAL_TERMS))[::-1]
    ax_a.barh(y, shares, color=BAR_COLOR, height=0.65)
    ax_a.set_yticks(y, [label for _, label, _ in DEAL_TERMS], fontsize=9)
    for yi, share, count in zip(y, shares, counts):
        ax_a.text(share + 0.6, yi, f"{share:.1f}%（{count}件）", va="center", fontsize=8.5)
    ax_a.set_xlim(0, 50)
    ax_a.set_xlabel("当てはまる案件の割合（%）")
    ax_a.set_title("(a) 取引条件ごとの割合", fontsize=10.5)

    ax_b.bar(terms_per_deal.index, terms_per_deal.values, color=BAR_COLOR, width=0.7)
    for x, v in terms_per_deal.items():
        ax_b.text(x, v + 2, f"{v}", ha="center", fontsize=8.5)
    ax_b.set_xticks(terms_per_deal.index)
    ax_b.set_xlabel("1案件が当てはまる取引条件の数")
    ax_b.set_ylabel("件数")
    ax_b.set_title("(b) 1案件当たりの取引条件の数", fontsize=10.5)

    fig.tight_layout()
    OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FIGURES / "figure3_4_distribution_of_deal_terms.png")
    print(terms_per_deal.to_dict(), "mean", round(df[columns].fillna(0).sum(axis=1).mean(), 2))


if __name__ == "__main__":
    main()
