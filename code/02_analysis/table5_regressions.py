"""Regressions of the return on each deal term (Section 4.2; results in Chapter 5).

Dependent variable (argument):
  R1 (default)  100 x ln(1 + R_i / 100), R_i = return from J+1 to the initial offer end date.
                The market is not subtracted; year dummies control for market movements
                (Hsieh and Walkling 2005).
  W1            the same period, market-adjusted (TOPIX subtracted), no year dummies (robustness)

Sample: the 403 deals of the analysis sample, split into partial offers, pinned full
offers (|S_i| <= 1%) and free full offers. With the argument --include-boundary-deals the
4 deals excluded by the filing rule (config.DEALS_EXCLUDED_BY_FILING_RULE) are added back
(407 deals, robustness check of the sample rule).

  (1) partial offers: mean return for S_i > 2% and S_i <= 2%, t-test against 0
  (2) terms in the registration statement: in free full offers and in all deals,
        y = a + b x term + c x S_i (+ partial offer dummy in all deals) (+ year dummies for R1)
      HC1 standard errors; * p < .10, ** p < .05
  (3) terms in the opinion statement (shareholder benefits, parent-subsidiary listing):
      all deals, full offers, free full offers
  (4) pinned full offers: the same regressions (terms should have no effect if the price is pinned)
  (5) (1)-(4) for deals announced on or after the METI guidelines (2023-08-31)

Output  output/tables/table5_regressions_{R1|W1}[_including_boundary_deals].csv
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (DEAL_TERMS, GUIDELINE_DATE, OUTPUT_TABLES,  # noqa: E402
                    PARTIAL_OFFER_GAP_THRESHOLD_PCT, PINNED_THRESHOLD_PCT)
from sample import load_analysis_table, load_sample  # noqa: E402

warnings.filterwarnings("ignore")

REGISTRATION_STATEMENT_TERMS = [
    "term_competitive_bidding", "term_no_price_increase_confirmed_in_negotiation_with_target",
    "term_investment_fund_involved_in_acquirer", "term_management_buyout_without_fund",
    "term_no_tender_or_non_tender_agreement_with_shareholders", "term_board_does_not_recommend_tender",
    "term_pending_regulatory_approval", "term_no_borrowing_or_equity_financing_planned",
]
OPINION_STATEMENT_TERMS = ["term_abolishes_shareholder_benefits", "term_resolves_parent_subsidiary_listing"]


def load(include_boundary_deals: bool) -> pd.DataFrame:
    if not include_boundary_deals:
        return load_sample()
    table = load_analysis_table()   # the 4 boundary deals have excluded_by_filing_rule = 1
    return table[table.return_to_initial_end_pct.notna() & table.price_gap_at_start_pct.notna()].copy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="R1", choices=["R1", "W1"])
    parser.add_argument("--include-boundary-deals", action="store_true")
    args = parser.parse_args()

    df = load(args.include_boundary_deals)
    column = "return_to_initial_end_pct" if args.target == "R1" else "market_adjusted_return_to_initial_end_pct"
    df["y"] = 100 * np.log1p(df[column] / 100)
    df = df[df.y.notna() & df.price_gap_at_start_pct.notna()]
    year_dummies = args.target == "R1"

    def regress(sub, term, controls=()):
        """Coefficient and p-value of `term`; not estimated if fewer than 2 deals have or lack the term."""
        sub = sub[sub[term].notna()]
        x = sub[[term, "price_gap_at_start_pct", *controls]].astype(float)
        if year_dummies:   # the earliest year in the sample is the base year
            x = x.join(pd.get_dummies(sub.announcement_year.astype(str), prefix="year", drop_first=True).astype(float))
        k = int((x[term] != 0).sum())
        if k < 2 or len(sub) - k < 2:
            return dict(coefficient=np.nan, p_value=np.nan, deals_with_term=k, deals_in_sample=len(sub))
        r = sm.OLS(sub.y.astype(float), sm.add_constant(x)).fit(cov_type="HC1")
        return dict(coefficient=round(r.params[term], 4), p_value=round(r.pvalues[term], 4),
                    deals_with_term=k, deals_in_sample=len(sub))

    rows = []

    def add(section, item, result):
        p = result["p_value"]
        rows.append({"section": section, "item": item, **result,
                     "significance": "**" if p < .05 else "*" if p < .1 else ""})

    def all_results(s, prefix):
        partial = s.term_partial_tender_offer == 1
        pinned = s.price_gap_at_start_pct.abs() <= PINNED_THRESHOLD_PCT
        free, pinned_full = s[~partial & ~pinned], s[~partial & pinned]
        g = PARTIAL_OFFER_GAP_THRESHOLD_PCT
        high, low = s[partial & (s.price_gap_at_start_pct > g)], s[partial & (s.price_gap_at_start_pct <= g)]
        for label, sub in [(f"価格差{g:.0f}%超の平均（0と比較）", high), (f"価格差{g:.0f}%以下の平均（0と比較）", low)]:
            add(f"{prefix}(1) 部分買付け", label,
                dict(coefficient=round(sub.y.mean(), 4), p_value=round(stats.ttest_1samp(sub.y, 0).pvalue, 4),
                     deals_with_term=len(sub), deals_in_sample=int(partial.sum())))
        for t in REGISTRATION_STATEMENT_TERMS:
            add(f"{prefix}(2) 自由に動く全部買付け", DEAL_TERMS[t], regress(free, t))
        for t in REGISTRATION_STATEMENT_TERMS[:4]:
            add(f"{prefix}(2) 全体", DEAL_TERMS[t], regress(s, t, ["term_partial_tender_offer"]))
        for t in OPINION_STATEMENT_TERMS:
            add(f"{prefix}(3) 全体", DEAL_TERMS[t], regress(s, t, ["term_partial_tender_offer"]))
            add(f"{prefix}(3) 全部買付け", DEAL_TERMS[t], regress(s[~partial], t))
            add(f"{prefix}(3) 自由に動く全部買付け", DEAL_TERMS[t], regress(free, t))
        for t in REGISTRATION_STATEMENT_TERMS[:4]:
            add(f"{prefix}(4) 張り付いた全部買付け", DEAL_TERMS[t], regress(pinned_full, t))

    all_results(df, "")
    all_results(df[df.announcement_date >= GUIDELINE_DATE], "(5) 指針後 ")
    result = pd.DataFrame(rows)
    name = f"table5_regressions_{args.target}" + ("_including_boundary_deals" if args.include_boundary_deals else "")
    result.to_csv(OUTPUT_TABLES / f"{name}.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(f"sample {len(df)} deals (dependent variable {args.target})")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
