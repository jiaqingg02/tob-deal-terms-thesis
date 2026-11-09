"""Robustness (appendix): the equation with a dummy for deals pinned to the offer price.

The main equation (equation.py) has no pinned dummy. Here the dummy |S_i| <= T is added for
T in {0.5, 1, 2, 3}% (PRICE_GAP_TERMS_WITH_PINNED) to show that the results do not depend on
whether, and where, such a threshold is drawn. Each of the 10 deal terms is added one at a time.
Dependent variable: y = 100 x ln(1 + R_i / 100) with year dummies; OLS, HC1 standard errors.

Output  output/tables/robustness_thresholds.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEAL_TERMS, OUTPUT_TABLES  # noqa: E402
from equation import (DEAL_TERMS_EXCEPT_PARTIAL, PRICE_GAP_TERMS_WITH_PINNED, add_equation_columns,  # noqa: E402
                      regress_on_equation)
from sample import load_sample  # noqa: E402

warnings.filterwarnings("ignore")

PINNED_THRESHOLDS_PCT = [0.5, 1, 2, 3]


def main():
    s = load_sample()
    s["y"] = 100 * np.log1p(s.return_to_initial_end_pct / 100)
    rows = []
    for threshold in PINNED_THRESHOLDS_PCT:
        d = add_equation_columns(s, pinned_threshold_pct=threshold)
        for term in DEAL_TERMS_EXCEPT_PARTIAL:
            result, data = regress_on_equation(d, "y", [term], PRICE_GAP_TERMS_WITH_PINNED)
            p = result.pvalues[term]
            rows.append({"check": "張り付きの閾値", "pinned_threshold_pct": threshold,
                         "deals_pinned": int(data["pinned"].sum()), "item": DEAL_TERMS[term],
                         "coefficient": round(result.params[term], 4), "p_value": round(p, 4),
                         "significance": "**" if p < .05 else "*" if p < .1 else "",
                         "deals_with_term": int(data[term].sum()), "deals_in_sample": len(data)})
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_TABLES / "robustness_thresholds.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 220)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
