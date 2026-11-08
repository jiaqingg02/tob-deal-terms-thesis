"""Tables 3.2 and 3.3.

Table 3.2: number of deals by announcement year (403 deals).
Table 3.3: descriptive statistics of the return R_i and the price gap S_i (403 deals).

Outputs
  output/tables/table3_2_deals_by_year.csv
  output/tables/table3_3_descriptive_statistics.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_TABLES  # noqa: E402
from sample import load_sample  # noqa: E402


def describe(x: pd.Series) -> dict:
    """Mean, standard deviation, minimum, median and maximum, as reported in the paper."""
    return {"平均": x.mean(), "標準偏差": x.std(ddof=1), "最小": x.min(),
            "中央値": x.median(), "最大": x.max()}


def main():
    df = load_sample()

    by_year = df["announcement_year"].value_counts().sort_index()
    by_year["合計"] = by_year.sum()
    table32 = by_year.to_frame("件数").T
    table32.columns.name = "公表年"
    table32.to_csv(OUTPUT_TABLES / "table3_2_deals_by_year.csv", encoding="utf-8-sig")

    table33 = pd.DataFrame({"収益率R_i（%）": describe(df["return_to_initial_end_pct"]),
                            "価格差S_i（%）": describe(df["price_gap_at_start_pct"])}).T.round(2)
    table33.index.name = "変数"
    table33.to_csv(OUTPUT_TABLES / "table3_3_descriptive_statistics.csv", encoding="utf-8-sig")

    print(table32.to_string())
    print(table33.to_string())


if __name__ == "__main__":
    main()
