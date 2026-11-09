"""The one equation used for both the regressions and the prediction (Sections 4.1-4.3).

    y_i = a + g * max(S_i, 0) + d * P_i + t * P_i * max(S_i, 0)
          + sum_k f_k * X_ik  (+ year dummies in the regressions)  + e_i

  max(S_i, 0)  return from buying at the close on the return start date and tendering at the
               offer price; it is 0 when the stock price is above the offer price, because
               shareholders then do not tender (tendering is a right, not an obligation)
  pinned_i     1 if |S_i| <= config.PINNED_THRESHOLD_PCT (the stock price is pinned to the offer price).
               Not in the main equation: deals pinned to the offer price have S_i close to 0 and hence
               max(S_i, 0) close to 0 already. The equation with pinned_i added
               (PRICE_GAP_TERMS_WITH_PINNED) is reported in the appendix as a robustness check.
  P_i          1 for a partial offer; P_i * max(S_i, 0) lets the slope of max(S_i, 0) differ,
               because only part of the tendered shares is bought in a partial offer
  X_ik         the other 10 deal terms (DEAL_TERMS_EXCEPT_PARTIAL)

All quantities are computed from information available at the close of the return start date.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PINNED_THRESHOLD_PCT  # noqa: E402

PRICE_GAP_TERMS = ["tender_payoff_pct", "term_partial_tender_offer", "partial_x_tender_payoff_pct"]
PRICE_GAP_TERMS_WITH_PINNED = [*PRICE_GAP_TERMS, "pinned"]
PARTIAL_OFFER_TERMS = ["term_partial_tender_offer", "partial_x_tender_payoff_pct"]

DEAL_TERMS_EXCEPT_PARTIAL = [
    "term_competitive_bidding", "term_no_price_increase_confirmed_in_negotiation_with_target",
    "term_investment_fund_involved_in_acquirer", "term_management_buyout_without_fund",
    "term_no_tender_or_non_tender_agreement_with_shareholders", "term_board_does_not_recommend_tender",
    "term_pending_regulatory_approval", "term_no_borrowing_or_equity_financing_planned",
    "term_abolishes_shareholder_benefits", "term_resolves_parent_subsidiary_listing",
]


def add_equation_columns(df: pd.DataFrame, pinned_threshold_pct: float = PINNED_THRESHOLD_PCT) -> pd.DataFrame:
    """Add the price-gap columns of the equation (in % of the stock price)."""
    df = df.copy()
    gap = df["price_gap_at_start_pct"]
    df["term_partial_tender_offer"] = df["term_partial_tender_offer"].fillna(0)
    df["tender_payoff_pct"] = gap.clip(lower=0)
    df["pinned"] = (gap.abs() <= pinned_threshold_pct).astype(float).where(gap.notna())
    df["partial_x_tender_payoff_pct"] = df["term_partial_tender_offer"] * df["tender_payoff_pct"]
    return df


def year_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """Dummies for the announcement year; the earliest year in the data is the base year."""
    return pd.get_dummies(df["announcement_year"].astype(str), prefix="year", drop_first=True).astype(float)


def regress_on_equation(df: pd.DataFrame, y: str, terms: list, price_gap_terms: list = PRICE_GAP_TERMS,
                        with_year_dummies: bool = True):
    """OLS of y on the equation: price_gap_terms + terms (+ year dummies), HC1 standard errors.

    Deals with a missing value in y or in any regressor are dropped (for the financing term,
    the 64 deals whose documents have no financing table). Returns the fitted statsmodels result and the data used.
    """
    import statsmodels.api as sm
    data = df[[y, *price_gap_terms, *terms]].dropna()
    x = data[[*price_gap_terms, *terms]].astype(float)
    if with_year_dummies:
        x = x.join(year_dummies(df.loc[data.index]))
    x = x.loc[:, x.std() > 0]   # drop columns that are constant in the sample (e.g. P in a sample without partial offers)
    return sm.OLS(data[y].astype(float), sm.add_constant(x)).fit(cov_type="HC1"), data
