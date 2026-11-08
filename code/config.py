"""Paths and fixed parameters shared by every program.

Every program imports this file, so paths and analysis parameters are set in one
place only. To run on another computer, set the environment variable
THESIS_RAW_DATA to the folder that holds the raw data (see README.md).
"""
import os
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

# Raw data that cannot be redistributed (stock prices, original documents).
# The folder must contain data/, data_old/ and program_vars/.
RAW_DATA = Path(os.environ.get("THESIS_RAW_DATA", REPOSITORY.parent))

INPUTS = REPOSITORY / "data" / "inputs"          # deal lists prepared from TDnet / EDINET
PROCESSED = REPOSITORY / "data" / "processed"    # files produced by code/01_dataprep
PUBLISHED = REPOSITORY / "data" / "published"    # data made in this study that are published in the repository
OUTPUT_TABLES = REPOSITORY / "output" / "tables"
OUTPUT_FIGURES = REPOSITORY / "output" / "figures"
for folder in (PROCESSED, PUBLISHED, OUTPUT_TABLES, OUTPUT_FIGURES):
    folder.mkdir(parents=True, exist_ok=True)

# ---- Analysis parameters (Sections 3.2, 3.3 and 4.1) -------------------------
FILING_DEADLINE_TIME = "15:00"          # documents must be filed before 15:00 on the return start date
ANNOUNCEMENT_CUTOFF_HOUR = 14           # announcement at or after 14:00 -> J is the next trading day
PINNED_THRESHOLD_PCT = 1.0              # |price gap| <= 1% -> stock price pinned to the offer price
GUIDELINE_DATE = "2023-08-31"           # METI "Guidelines for Corporate Takeovers"

# Deals that remain in the deal list but violate the filing rule of Section 3.2:
# the opinion statement was filed after 15:00 on the return start date (4477, 6736, 9362),
# or no original opinion statement exists on EDINET (5357).
DEALS_EXCLUDED_BY_FILING_RULE = [
    "4477_2025-05-07", "6736_2024-06-10", "9362_2024-10-18", "5357_2025-04-11",
]

# Expected sample sizes; the analysis programs stop if the data do not match.
EXPECTED_SAMPLE_SIZE = {"all": 403, "partial": 64, "pinned": 187}   # pinned: |price gap| <= PINNED_THRESHOLD_PCT, partial offers included

# ---- Names of the 11 deal terms (Section 3.4) ---------------------------------
# column name -> name used in the paper
DEAL_TERMS = {
    "term_partial_tender_offer": "部分買付け",
    "term_competitive_bidding": "入札・競合あり",
    "term_no_price_increase_confirmed_in_negotiation_with_target": "対象者との交渉による価格の引上げが確認されない",
    "term_investment_fund_involved_in_acquirer": "買付者へのファンドの関与",
    "term_management_buyout_without_fund": "MBO（ファンドの関与なし）",
    "term_no_tender_or_non_tender_agreement_with_shareholders": "株主との応募・不応募の合意の記載なし",
    "term_board_does_not_recommend_tender": "取締役会が応募を推奨しない",
    "term_pending_regulatory_approval": "許認可の承認待ち",
    "term_no_borrowing_or_equity_financing_planned": "買付資金に借入・出資の予定なし",
    "term_abolishes_shareholder_benefits": "株主優待の廃止",
    "term_resolves_parent_subsidiary_listing": "親子上場の解消",
}
