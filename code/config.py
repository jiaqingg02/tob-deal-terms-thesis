"""Paths and fixed parameters shared by every program.

Every program imports this file, so paths and analysis parameters are set in one
place only. To run on another computer, set the environment variable
THESIS_RAW_DATA to the folder that holds the raw data (see README.md).
"""
import os
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

# Raw data that cannot be redistributed (stock prices, original documents).
# The folder must contain data/, data_old/, fill_summary/ and program_vars/.
RAW_DATA = Path(os.environ.get("THESIS_RAW_DATA", REPOSITORY.parent))

INPUTS = REPOSITORY / "data" / "inputs"          # deal lists prepared from TDnet / EDINET
PROCESSED = REPOSITORY / "data" / "processed"    # files produced by code/01_dataprep
OUTPUT_TABLES = REPOSITORY / "output" / "tables"
OUTPUT_FIGURES = REPOSITORY / "output" / "figures"
for folder in (PROCESSED, OUTPUT_TABLES, OUTPUT_FIGURES):
    folder.mkdir(parents=True, exist_ok=True)

# ---- Analysis parameters (Sections 3.2, 3.3 and 4.1) -------------------------
FILING_DEADLINE_TIME = "15:00"          # documents must be filed before 15:00 on the return start date
ANNOUNCEMENT_CUTOFF_HOUR = 14           # announcement at or after 14:00 -> J is the next trading day
PINNED_THRESHOLD_PCT = 1.0              # |price gap| <= 1% -> stock price pinned to the offer price
PARTIAL_OFFER_GAP_THRESHOLD_PCT = 2.0   # partial offers are split at a price gap of 2%
GUIDELINE_DATE = "2023-08-31"           # METI "Guidelines for Corporate Takeovers"

# Deals that remain in the deal list but violate the filing rule of Section 3.2:
# the opinion statement was filed after 15:00 on the return start date (4477, 6736, 9362),
# or no original opinion statement exists on EDINET (5357).
DEALS_EXCLUDED_BY_FILING_RULE = [
    "4477_2025-05-07", "6736_2024-06-10", "9362_2024-10-18", "5357_2025-04-11",
]

# Expected sample sizes; the analysis programs stop if the data do not match.
EXPECTED_SAMPLE_SIZE = {"all": 403, "partial": 64, "pinned": 184, "free": 155}

# ---- Names of the 11 deal terms (Section 3.4) ---------------------------------
# column name -> name used in the paper
DEAL_TERMS = {
    "term_partial_tender_offer": "部分買付け",
    "term_competitive_bidding": "入札・競合あり",
    "term_no_price_increase_in_negotiation": "交渉で値上げされていない",
    "term_acquirer_is_investment_fund": "買付者がファンド",
    "term_management_buyout": "MBO",
    "term_no_tender_agreement_with_major_shareholder": "大株主の応募契約なし",
    "term_board_opinion_is_neutral": "取締役会が中立",
    "term_pending_regulatory_approval": "許認可の承認待ち",
    "term_financed_by_own_funds": "自己資金",
    "term_abolishes_shareholder_benefits": "株主優待の廃止",
    "term_resolves_parent_subsidiary_listing": "親子上場の解消",
}
