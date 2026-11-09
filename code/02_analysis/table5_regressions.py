"""Regressions of the return on the deal terms with the one equation of Section 4.1 (results in Chapter 5).

Equation (equation.py):
  y_i = a + g max(S_i, 0) + d P_i + t P_i max(S_i, 0) + f X_i (+ year dummies) + e_i
  OLS, HC1 standard errors; * p < .10, ** p < .05; p-values are rounded to 4 digits.

Dependent variable (argument):
  R1 (default)  100 x ln(1 + R_i / 100), R_i = return from J+1 to the initial offer end date.
                The market is not subtracted; year dummies control for market movements
                (Hsieh and Walkling 2005).
  W1            the same period, market-adjusted (TOPIX subtracted), no year dummies (robustness)

Sample: the 403 deals of the analysis sample. With the argument --include-boundary-deals the
4 deals excluded by the filing rule (config.DEALS_EXCLUDED_BY_FILING_RULE) are added back
(407 deals, robustness check of the sample rule).

  (1) main table: each of the 10 deal terms X_i added one at a time
  (2) the partial offer terms P_i and P_i max(S_i, 0) in the equation without deal terms
  (3) joint model: the 10 deal terms together, in the deals where every term has a value
      (the financing term has no value for the 64 deals whose documents have no financing table), and the Wald test that all 10 are 0
  (4) robustness (Appendix C): (1) with the linear price gap S_i added
  (5) robustness: (1) for deals announced on or after the METI guidelines (2023-08-31)
  (6) robustness (appendix): (1) and (3) with the pinned dummy (|S_i| <= 1%) added

Output  output/tables/table5_regressions_{R1|W1}[_including_boundary_deals].csv
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEAL_TERMS, GUIDELINE_DATE, OUTPUT_TABLES  # noqa: E402
from equation import (DEAL_TERMS_EXCEPT_PARTIAL, PARTIAL_OFFER_TERMS, PRICE_GAP_TERMS,  # noqa: E402
                      PRICE_GAP_TERMS_WITH_PINNED,
                      add_equation_columns, regress_on_equation)
from sample import load_analysis_table, load_sample  # noqa: E402

warnings.filterwarnings("ignore")

TERM_NAMES = {**DEAL_TERMS, "partial_x_tender_payoff_pct": "部分買付け×max(価格差, 0)",
              "pinned": "張り付き（価格差の絶対値が1%以下）"}


def load(include_boundary_deals: bool) -> pd.DataFrame:
    if not include_boundary_deals:
        return load_sample()
    table = load_analysis_table()   # the 4 boundary deals have excluded_by_filing_rule = 1
    return table[table.return_to_initial_end_pct.notna() & table.price_gap_at_start_pct.notna()].copy()


def significance(p):
    return "**" if p < .05 else "*" if p < .1 else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="R1", choices=["R1", "W1"])
    parser.add_argument("--include-boundary-deals", action="store_true")
    args = parser.parse_args()

    df = add_equation_columns(load(args.include_boundary_deals))
    column = "return_to_initial_end_pct" if args.target == "R1" else "market_adjusted_return_to_initial_end_pct"
    df["y"] = 100 * np.log1p(df[column] / 100)
    df = df[df.y.notna()]
    with_years = args.target == "R1"
    rows = []

    def add(section, term, result, data):
        if term not in result.params:   # the term is constant in this sample
            return
        p = result.pvalues[term]
        rows.append({"section": section, "item": TERM_NAMES[term],
                     "coefficient": round(result.params[term], 4), "p_value": round(p, 4),
                     "significance": significance(p),
                     "deals_with_term": int((data[term] != 0).sum()), "deals_in_sample": len(data)})

    def one_term_at_a_time(sub, section, price_gap_terms=PRICE_GAP_TERMS):
        for term in DEAL_TERMS_EXCEPT_PARTIAL:
            result, data = regress_on_equation(sub, "y", [term], price_gap_terms, with_years)
            add(section, term, result, data)

    one_term_at_a_time(df, "(1) 主表：取引条件を1つずつ加える")

    result, data = regress_on_equation(df, "y", [], PRICE_GAP_TERMS, with_years)
    for term in PARTIAL_OFFER_TERMS:
        add("(2) 部分買付けの項（取引条件を加えない式）", term, result, data)

    def joint_model(section, price_gap_terms):
        result, data = regress_on_equation(df, "y", DEAL_TERMS_EXCEPT_PARTIAL, price_gap_terms, with_years)
        for term in DEAL_TERMS_EXCEPT_PARTIAL:
            add(section, term, result, data)
        present = [t for t in DEAL_TERMS_EXCEPT_PARTIAL if t in result.params]
        restriction = np.zeros((len(present), len(result.params)))
        for i, term in enumerate(present):
            restriction[i, list(result.params.index).index(term)] = 1
        wald_p = float(result.wald_test(restriction, scalar=True).pvalue)
        rows.append({"section": section, "item": f"{len(present)}の取引条件の係数がすべて0（Wald検定）",
                     "p_value": round(wald_p, 4), "significance": significance(wald_p), "deals_in_sample": len(data)})

    joint_model("(3) 同時モデル：10の取引条件を同時に加える", PRICE_GAP_TERMS)

    df["price_gap_linear_pct"] = df["price_gap_at_start_pct"]
    one_term_at_a_time(df, "(4) 頑健性（付録C）：直線の価格差 S を加える",
                       ["price_gap_linear_pct", *PRICE_GAP_TERMS])
    one_term_at_a_time(df[df.announcement_date >= GUIDELINE_DATE], "(5) 頑健性：指針後の案件")
    one_term_at_a_time(df, "(6) 頑健性（付録）：張り付きの変数を加える（1つずつ）", PRICE_GAP_TERMS_WITH_PINNED)
    result, data = regress_on_equation(df, "y", [], PRICE_GAP_TERMS_WITH_PINNED, with_years)
    add("(6) 頑健性（付録）：張り付きの変数を加える（1つずつ）", "pinned", result, data)
    joint_model("(6) 頑健性（付録）：張り付きの変数を加える（同時モデル）", PRICE_GAP_TERMS_WITH_PINNED)

    result = pd.DataFrame(rows)
    name = f"table5_regressions_{args.target}" + ("_including_boundary_deals" if args.include_boundary_deals else "")
    result.to_csv(OUTPUT_TABLES / f"{name}.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(f"sample {len(df)} deals (dependent variable {args.target})")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
