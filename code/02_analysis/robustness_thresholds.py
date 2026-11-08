"""Robustness to the thresholds used to split the sample (Chapter 5, robustness).

Dependent variable: y = 100 x ln(1 + R_i / 100) with year dummies, as in table5_regressions.py.

  (1) pinned threshold T in {0.5, 1, 2, 3}%: effects of three deal terms in free and pinned full offers
  (2) partial offers, gap threshold G in {0, ..., 5}%: mean y above and at or below G, t-test against 0
  (3) partial offers without a threshold: y on the price gap, and Spearman rank correlation

Output  output/tables/robustness_thresholds.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEAL_TERMS, OUTPUT_TABLES  # noqa: E402
from sample import load_sample  # noqa: E402

warnings.filterwarnings("ignore")


def regress(sub, term):
    x = sub[[term, "price_gap_at_start_pct"]].astype(float).join(
        pd.get_dummies(sub.announcement_year.astype(str), prefix="year", drop_first=True).astype(float))
    r = sm.OLS(sub.y.astype(float), sm.add_constant(x)).fit(cov_type="HC1")
    return dict(coefficient=round(r.params[term], 2), p_value=round(r.pvalues[term], 3),
                deals_with_term=int(sub[term].sum()), deals_in_sample=len(sub))


def main():
    s = load_sample()
    s["y"] = 100 * np.log1p(s.return_to_initial_end_pct / 100)
    partial = s.term_partial_tender_offer == 1
    rows = []
    for threshold in [0.5, 1, 2, 3]:
        pinned = s.price_gap_at_start_pct.abs() <= threshold
        for group, sub in [("自由に動く全部買付け", s[~partial & ~pinned]), ("張り付いた全部買付け", s[~partial & pinned])]:
            for term in ["term_competitive_bidding", "term_investment_fund_involved_in_acquirer", "term_resolves_parent_subsidiary_listing"]:
                rows.append({"check": "(1) 張り付きの閾値", "threshold_pct": threshold, "group": group,
                             "item": DEAL_TERMS[term], **regress(sub, term)})
    p = s[partial]
    for threshold in range(6):
        for side, sub in [("超", p[p.price_gap_at_start_pct > threshold]), ("以下", p[p.price_gap_at_start_pct <= threshold])]:
            rows.append({"check": "(2) 部分買付けの価格差の閾値", "threshold_pct": threshold, "group": f"価格差{threshold}%{side}",
                         "item": "平均収益（0と比較）", "coefficient": round(sub.y.mean(), 2),
                         "p_value": round(stats.ttest_1samp(sub.y, 0).pvalue, 3), "deals_in_sample": len(sub)})
    r = sm.OLS(p.y, sm.add_constant(p[["price_gap_at_start_pct"]].astype(float))).fit(cov_type="HC1")
    rows.append({"check": "(3) 部分買付け・閾値なし", "group": "部分買付け", "item": "価格差の係数",
                 "coefficient": round(r.params["price_gap_at_start_pct"], 3),
                 "p_value": round(r.pvalues["price_gap_at_start_pct"], 3), "deals_in_sample": len(p)})
    rho = stats.spearmanr(p.price_gap_at_start_pct, p.y)
    rows.append({"check": "(3) 部分買付け・閾値なし", "group": "部分買付け", "item": "価格差と収益の順位相関",
                 "coefficient": round(rho[0], 3), "p_value": round(rho[1], 3), "deals_in_sample": len(p)})
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_TABLES / "robustness_thresholds.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 220)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
