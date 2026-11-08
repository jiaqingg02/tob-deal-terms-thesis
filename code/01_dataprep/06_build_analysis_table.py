"""Combine all deal-level variables into one analysis table (one row per deal).

Rows: the 413 deals whose documents were read (data/inputs/標本413.csv).
  excluded_by_filing_rule = 1 for the 4 deals that violate the filing rule of Section 3.2
                            (config.DEALS_EXCLUDED_BY_FILING_RULE); they are kept only for
                            the robustness check that adds them back
  in_analysis_sample      = 1 for the 403 deals that pass the filing rule and have both a
                            price gap and a return (Table 3.1)
Deals that pass the filing rule but lack a price gap are used only as training data in the
prediction comparison when their return exists.

Inputs
  data/inputs/標本413.csv, prepared_data_corrected.csv (2022 onward), prepared_old.csv (2019, 2021)
  data/processed/price_gap.csv, return_to_initial_end.csv, sentiment_scores.csv, deal_terms.csv
Output
  data/processed/analysis_table.csv   (variables are described in data/codebook.csv)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEAL_TERMS, DEALS_EXCLUDED_BY_FILING_RULE, INPUTS, PROCESSED  # noqa: E402

# Column names in the input deal lists (made by an earlier program) -> descriptive names.
INPUT_COLUMNS = {
    "code": "target_securities_code",
    "event_date": "announcement_date",
    "j1_date": "return_start_date",
    "edinet_todokede": "registration_statement_document_id",
    "edinet_iken": "opinion_statement_document_id",
    "todokede_filed": "registration_statement_filed_at",
    "iken_filed": "opinion_statement_filed_at",
    "avail_post": "document_availability_at_return_start",
    "sando": "board_supports_and_recommends_tender",
    "contested": "board_opposes_or_reserves_opinion",
    "comp2": "second_or_later_offer_for_same_target",
    "staged": "announced_in_multiple_stages",
    "media_any": "has_news_before_announcement",
    "media_cnt": "news_count_before_announcement",
    "mkt": "topix_return_before_announcement_ratio",
    "log_mktcap": "log_market_capitalization",
    "seg_prime": "listed_on_prime_market",
    "seg_growth": "listed_on_growth_market",
}
NUMERIC = ["board_supports_and_recommends_tender", "board_opposes_or_reserves_opinion",
           "second_or_later_offer_for_same_target", "announced_in_multiple_stages",
           "has_news_before_announcement", "news_count_before_announcement",
           "topix_return_before_announcement_ratio", "log_market_capitalization",
           "listed_on_prime_market", "listed_on_growth_market"]

new = pd.read_csv(INPUTS / "prepared_data_corrected.csv", dtype={"code": str}, keep_default_na=False)
old = pd.read_csv(INPUTS / "prepared_old.csv", dtype={"code": str}, keep_default_na=False)
old = old[old.event_date.str[:4].isin(["2019", "2021"])]
for x in (new, old):
    x["deal_id"] = x.code + "_" + x.event_date
deals = pd.concat([new, old[~old.deal_id.isin(new.deal_id)]]).set_index("deal_id")
deals = deals[[c for c in INPUT_COLUMNS if c in deals.columns]].rename(columns=INPUT_COLUMNS)
for c in NUMERIC:
    deals[c] = pd.to_numeric(deals[c], errors="coerce")

deal_ids = pd.read_csv(INPUTS / "標本413.csv").key
table = deals.loc[deal_ids]
table.index.name = "deal_id"
table["announcement_year"] = table.announcement_date.str[:4].astype(int)

price_gap = pd.read_csv(PROCESSED / "price_gap.csv", index_col=0)
table = table.join(price_gap[["first_trading_day_after_announcement", "offer_premium_ratio",
                              "price_gap_at_start_ratio", "pinned_to_offer_price"]])
table["price_gap_at_start_pct"] = 100 * table.price_gap_at_start_ratio

returns = pd.read_csv(PROCESSED / "return_to_initial_end.csv", index_col=0)
table = table.join(returns[["return_to_initial_end_pct", "market_adjusted_return_to_initial_end_pct",
                            "initial_offer_end_trading_date"]])
table = table.join(pd.read_csv(PROCESSED / "sentiment_scores.csv", index_col=0))
table = table.join(pd.read_csv(PROCESSED / "deal_terms.csv", index_col=0)[list(DEAL_TERMS)])

table["excluded_by_filing_rule"] = table.index.isin(DEALS_EXCLUDED_BY_FILING_RULE).astype(int)
table["in_analysis_sample"] = ((table.excluded_by_filing_rule == 0)
                               & table.return_to_initial_end_pct.notna()
                               & table.price_gap_at_start_pct.notna()).astype(int)
table.to_csv(PROCESSED / "analysis_table.csv", encoding="utf-8-sig")
print("analysis table (rows, columns)", table.shape,
      "| analysis sample", int(table.in_analysis_sample.sum()))
