"""Robustness to the threshold of "pinned to the offer price" (Chapter 5, robustness).

The main equation of table5_regressions.py (equation.py) is estimated with the pinned
dummy defined by |S_i| <= T for T in {0.5, 1, 2, 3}% (1% is the main threshold,
config.PINNED_THRESHOLD_PCT). Each of the 10 deal terms is added one at a time.
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
from equation import DEAL_TERMS_EXCEPT_PARTIAL, add_equation_columns, regress_on_equation  # noqa: E402
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
            result, data = regress_on_equation(d, "y", [term])
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
