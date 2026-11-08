"""Table 3.1: Sample selection.

Rules are applied in this order:
  (1) tender offers announced in 2019, 2021 or January 2022 - June 2026 (2020 excluded)
  (2) drop deals whose registration statement or opinion statement was not filed
      before 15:00 on the return start date (J+1), or has no original document on EDINET
  (3) drop deals without a price gap, an initial offer end date, or prices up to that date

Inputs
  data/inputs/prepared_data_corrected.csv  2022-onward deals after de-duplication of the TDnet list
  data/inputs/prepared_old.csv             2019-2021 deals
  data/processed/analysis_table.csv         (via sample.load_sample)
Output
  output/tables/table3_1_sample_selection.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEALS_EXCLUDED_BY_FILING_RULE, INPUTS, OUTPUT_TABLES  # noqa: E402
from sample import load_sample  # noqa: E402

PERIOD_END = "2026-07-01"   # announcements on or after this date are outside the period

# One 2022-onward deal (鳥居) is in the de-duplicated TDnet list (409 deals) but not in
# prepared_data_corrected.csv (408 deals); it is counted as failing rule (2), as in Table 3.1.
# The step that removed it is in the upstream program that made prepared_data_corrected.csv
# (not in this repository), so it is added back here as a constant.
DEALS_WITHOUT_REGISTRATION_STATEMENT = 1


def main():
    new = pd.read_csv(INPUTS / "prepared_data_corrected.csv", dtype={"code": str})
    old = pd.read_csv(INPUTS / "prepared_old.csv", dtype={"code": str})
    old = old[old["event_date"].str[:4].isin(["2019", "2021"])]
    for x in (new, old):
        x["deal_id"] = x["code"] + "_" + x["event_date"]

    new_in_period = new[new["event_date"] < PERIOD_END]
    step1 = len(new_in_period) + DEALS_WITHOUT_REGISTRATION_STATEMENT + len(old)

    filed_on_time = lambda x: (x["avail_post"] == "ok") & ~x["deal_id"].isin(DEALS_EXCLUDED_BY_FILING_RULE)
    step2 = int(filed_on_time(new_in_period).sum() + filed_on_time(old).sum())
    step3 = len(load_sample())

    table = pd.DataFrame({"件数": [step1, -(step1 - step2), -(step2 - step3), step3]}, index=[
        "2019年〜2026年6月に公表された公開買付け（2020年を除く）",
        "書類が収益率の計算を始める日の15時までに提出されていない案件",
        "価格差、当初の買付期間の末日、またはその日までの株価が得られない案件",
        "分析対象",
    ])
    table.index.name = "行"
    table.to_csv(OUTPUT_TABLES / "table3_1_sample_selection.csv", encoding="utf-8-sig")
    print(table.to_string())


if __name__ == "__main__":
    main()
