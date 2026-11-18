"""Table 5.2: Estimate of equation (4.2) without deal terms (403 deals).

Same estimate as section (2) of table5_regressions.py and figure5_3 (OLS of the log return y_i on
max(S_i,0), P_i, P_i*max(S_i,0) and year dummies; HC1 standard errors). The table gives the
constant alpha, gamma, delta, theta, the slope for partial offers gamma + theta (Wald test of
gamma + theta = 0), the number of deals and R squared. The estimated equation is printed
so that the equation in the text can be checked.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_TABLES  # noqa: E402
from equation import add_equation_columns, regress_on_equation  # noqa: E402
from sample import load_sample  # noqa: E402

warnings.filterwarnings("ignore")


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def main():
    df = add_equation_columns(load_sample())
    df["y"] = 100 * np.log1p(df["return_to_initial_end_pct"] / 100)
    result, data = regress_on_equation(df, "y", [])
    rows = []
    for name, symbol, column in [("定数項", "alpha", "const"),
                                 ("価格差の正の部分 max(S_i,0)", "gamma", "tender_payoff_pct"),
                                 ("部分買付け P_i", "delta", "term_partial_tender_offer"),
                                 ("部分買付け×価格差の正の部分 P_i max(S_i,0)", "theta", "partial_x_tender_payoff_pct")]:
        b, p = float(result.params[column]), float(result.pvalues[column])
        rows.append({"項": name, "記号": symbol, "係数": round(b, 2), "有意": stars(p), "p値": round(p, 3)})
    slope = float(result.params["tender_payoff_pct"] + result.params["partial_x_tender_payoff_pct"])
    p = float(result.t_test("tender_payoff_pct + partial_x_tender_payoff_pct = 0").pvalue)
    rows.append({"項": "部分買付けにおける傾き", "記号": "gamma + theta", "係数": round(slope, 2), "有意": stars(p), "p値": round(p, 3)})
    rows.append({"項": "件数", "記号": "", "係数": len(data), "有意": "", "p値": ""})
    rows.append({"項": "決定係数", "記号": "", "係数": round(float(result.rsquared), 2), "有意": "", "p値": ""})
    table = pd.DataFrame(rows)
    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUTPUT_TABLES / "table5_2_equation_without_deal_terms.csv", index=False, encoding="utf-8-sig")
    print(table.to_string(index=False))
    r = result.params
    print(f"y_hat = {r['const']:.2f} + {r['tender_payoff_pct']:.2f} max(S,0) {r['term_partial_tender_offer']:+.2f} P "
          f"{r['partial_x_tender_payoff_pct']:+.2f} P max(S,0) + year effects")


if __name__ == "__main__":
    main()
