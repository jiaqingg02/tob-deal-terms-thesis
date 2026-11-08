"""Table 4.1: Descriptive statistics of R_i and S_i by deal group (%).

Output  output/tables/table4_1_descriptive_statistics_by_group.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_TABLES  # noqa: E402
from sample import GROUP_LABELS, load_sample  # noqa: E402
from table3_2_and_3_3_deals_by_year_and_descriptive_statistics import describe  # noqa: E402


def main():
    df = load_sample()
    rows = {}
    for g in ("partial", "pinned", "free"):
        sub = df[df["deal_group"] == g]
        rows[f"{GROUP_LABELS[g]}　R_i"] = describe(sub["return_to_initial_end_pct"])
        rows[f"{GROUP_LABELS[g]}　S_i"] = describe(sub["price_gap_at_start_pct"])
    table = pd.DataFrame(rows).T.round(2)
    table.index.name = "案件の種類と変数"
    table.to_csv(OUTPUT_TABLES / "table4_1_descriptive_statistics_by_group.csv", encoding="utf-8-sig")
    print(table.to_string())


if __name__ == "__main__":
    main()
