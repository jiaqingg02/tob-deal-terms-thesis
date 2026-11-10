"""Figure 5.1: Coefficients of the 10 deal terms, each added one at a time to equation (4.2) (dependent variable R1).

The same regressions as section (1) of table5_regressions.py (OLS, HC1 standard errors, year dummies).
Each point is the coefficient and the bar is its 90% confidence interval, so a bar that does not cross 0
means the coefficient is significant at the 10% level. Filled blue points: p < .10; hollow grey points: not significant (shown in the legend).
The order of the terms is the order of Table 5.1; the coefficient with its stars is written on the right.

Output  output/figures/figure5_1_deal_term_coefficients.png
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEAL_TERMS, OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from figure_style import MINUS  # noqa: E402
from equation import DEAL_TERMS_EXCEPT_PARTIAL, add_equation_columns, regress_on_equation  # noqa: E402
from sample import load_sample  # noqa: E402

warnings.filterwarnings("ignore")
CONFIDENCE = 0.90


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""


def main():
    df = add_equation_columns(load_sample())
    df["y"] = 100 * np.log1p(df["return_to_initial_end_pct"] / 100)
    rows = []
    for term in DEAL_TERMS_EXCEPT_PARTIAL:
        result, _ = regress_on_equation(df, "y", [term])
        low, high = result.conf_int(alpha=1 - CONFIDENCE).loc[term]
        rows.append((DEAL_TERMS[term], result.params[term], low, high, result.pvalues[term]))

    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    ax.axvline(0, color="0.45", lw=0.9, ls="--", zorder=0)
    for i, (label, coef, low, high, p) in enumerate(rows):
        y = len(rows) - 1 - i
        significant = p < .1
        color = "#1f5fbf" if significant else "0.55"
        ax.plot([low, high], [y, y], color=color, lw=1.6, zorder=1)
        ax.scatter([coef], [y], s=36, zorder=2, color=color if significant else "white",
                   edgecolors=color, linewidths=1.2)
        ax.text(4.7, y, f"{coef:.2f}{stars(p)}".replace("-", MINUS), va="center", ha="left", fontsize=9,
                color="black" if significant else "0.35")
    ax.scatter([], [], s=36, color="#1f5fbf", edgecolors="#1f5fbf", linewidths=1.2, label="10%水準で有意")
    ax.scatter([], [], s=36, color="white", edgecolors="0.55", linewidths=1.2, label="有意でない")
    ax.legend(loc="upper right", bbox_to_anchor=(1.03, 1.08), frameon=False, fontsize=9, handletextpad=0.2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1], fontsize=10)
    ax.set_xlabel("係数（%ポイント）と90%信頼区間")
    ax.set_xlim(-4.5, 4.5)
    ax.text(4.7, len(rows) - 0.4, "係数", va="center", ha="left", fontsize=9)
    ax.set_xticks([-4, -2, 0, 2, 4], [f"{MINUS}4", f"{MINUS}2", "0", "2", "4"])
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.savefig(OUTPUT_FIGURES / "figure5_1_deal_term_coefficients.png", bbox_inches="tight")
    for label, coef, low, high, p in rows:
        print(f"{label}\t{coef:.2f}\t[{low:.2f}, {high:.2f}]\tp={p:.3f}")


if __name__ == "__main__":
    main()
