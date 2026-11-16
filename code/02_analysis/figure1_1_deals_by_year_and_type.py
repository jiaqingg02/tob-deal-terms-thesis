"""Figure 1.1: Number of tender offers in the sample by announcement year and type (403 deals).

Each deal is put in one type, in this order of priority: parent-subsidiary listing resolved, investment fund
involved in the acquirer, MBO without a fund, other. Only 3 deals have two of the first three terms
(2 parent + fund, 1 parent + MBO); they are counted as parent-subsidiary. 2026 covers January to June only.

Output  output/figures/figure1_1_deals_by_year_and_type.png  and  output/tables/figure1_1_deals_by_year_and_type.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_FIGURES, OUTPUT_TABLES  # noqa: E402
import figure_style  # noqa: F401,E402
from sample import load_sample  # noqa: E402

TYPES = [("term_resolves_parent_subsidiary_listing", "親子上場の解消", "#1f3f7a"),
         ("term_investment_fund_involved_in_acquirer", "買付者へのファンドの関与", "#1f5fbf"),
         ("term_management_buyout_without_fund", "MBO（ファンドの関与なし）", "#8fb3e6"),
         (None, "その他", "#d9d9d9")]


def main():
    df = load_sample()
    df["year"] = pd.to_datetime(df["announcement_date"]).dt.year
    df["type"] = "その他"
    for term, label, _ in reversed(TYPES[:-1]):   # later assignments win, so the first type has priority
        df.loc[df[term] == 1, "type"] = label
    table = pd.crosstab(df["year"], df["type"])[[t[1] for t in TYPES]]
    table.to_csv(OUTPUT_TABLES / "figure1_1_deals_by_year_and_type.csv", encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(table))
    bottom = np.zeros(len(table))
    for _, label, color in TYPES:
        ax.bar(x, table[label], bottom=bottom, color=color, width=0.6, label=label, edgecolor="white", lw=0.5)
        bottom += table[label].to_numpy()
    for xi, total in zip(x, bottom):
        ax.text(xi, total + 1.5, f"{int(total)}", ha="center", va="bottom", fontsize=10)
    labels = [str(y) if y != 2026 else "2026\n（1〜6月）" for y in table.index]
    ax.set_xticks(x, labels)
    ax.set_ylabel("件数")
    ax.set_ylim(0, 120)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.savefig(OUTPUT_FIGURES / "figure1_1_deals_by_year_and_type.png")
    print(table.assign(合計=table.sum(axis=1)).to_string())
    print(table.sum().to_string())


if __name__ == "__main__":
    main()
