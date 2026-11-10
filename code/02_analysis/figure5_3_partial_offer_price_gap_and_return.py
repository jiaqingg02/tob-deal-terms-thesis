"""Figure 5.3: Positive part of the price gap max(S_i, 0) and the log return y_i, full offers vs partial offers (403 deals).

Points: deals (hollow circles and solid line = full offers, filled circles and dashed line = partial offers). Lines: the equation of Section 4.1 without deal terms,
estimated as in section (2) of table5_regressions.py (OLS, HC1, year dummies):
  full offers     y = c + g x
  partial offers  y = c + d + (g + t) x
where x = max(S_i, 0), g, d, t are the estimated coefficients and c is the constant plus the average year effect
(the mean of the fitted values minus the price-gap part). Each line is drawn over the range of x of its deals.
Both axes are truncated at 60 (x) and -30 / 60 (y); values outside are drawn on the edge.
The x axis is labelled with the price gap; values of S_i <= 0 are drawn at 0. The slopes are printed so that the numbers in the text can be checked.

Output  output/figures/figure5_3_partial_offer_price_gap_and_return.png
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from figure_style import MINUS  # noqa: E402
from equation import add_equation_columns, regress_on_equation  # noqa: E402
from sample import load_sample  # noqa: E402

warnings.filterwarnings("ignore")
X_HI, Y_LO, Y_HI = 60.0, -30.0, 60.0


def main():
    df = add_equation_columns(load_sample())
    df["y"] = 100 * np.log1p(df["return_to_initial_end_pct"] / 100)
    result, data = regress_on_equation(df, "y", [])
    g = result.params["tender_payoff_pct"]
    d = result.params["term_partial_tender_offer"]
    t = result.params["partial_x_tender_payoff_pct"]
    gap_part = g * data["tender_payoff_pct"] + d * data["term_partial_tender_offer"] + t * data["partial_x_tender_payoff_pct"]
    c = (result.fittedvalues - gap_part).mean()

    partial = data["term_partial_tender_offer"] == 1
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    ax.axhline(0, color="0.85", lw=0.6, zorder=0)
    for mask, label, intercept, slope, face, edge, line_style, z in [
            (~partial, f"全部買付け（{(~partial).sum()}件）", c, g, "none", "0.35", "-", 2),
            (partial, f"部分買付け（{partial.sum()}件）", c + d, g + t, "black", "black", "--", 3)]:
        x = data.loc[mask, "tender_payoff_pct"]
        ax.scatter(np.clip(x, 0, X_HI), np.clip(data.loc[mask, "y"], Y_LO, Y_HI), s=18, facecolors=face,
                   edgecolors=edge, linewidths=0.7, zorder=z)
        line_x = np.array([0, min(x.max(), X_HI)])
        ax.plot(line_x, intercept + slope * line_x, color="black", lw=1.4, ls=line_style, zorder=4)
        ax.plot([], [], marker="o", ls=line_style, color="black", mfc=face, mec=edge, label=label)
        print(f"{label}: slope {slope:.3f}, intercept {intercept:.3f}")
    ax.set_xticks([0, 20, 40, 60], ["0", "20", "40", "60以上"])
    ax.set_yticks([-30, 0, 20, 40, 60], [f"{MINUS}30以下", "0", "20", "40", "60以上"])
    ax.set_xlim(-2, X_HI + 2)
    ax.set_ylim(Y_LO - 3, Y_HI + 3)
    ax.set_xlabel("計算開始日の価格差（%）")
    ax.set_ylabel("対数に変換した収益率")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    fig.savefig(OUTPUT_FIGURES / "figure5_3_partial_offer_price_gap_and_return.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
