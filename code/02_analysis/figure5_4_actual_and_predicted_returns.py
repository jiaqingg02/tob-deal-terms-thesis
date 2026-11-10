"""Figure 5.4: Actual return R_i vs. predicted return for the three prediction models (403 deals).

Reads the per-deal prediction errors written by table5_prediction_errors.py (R1, deals split by company
into 10 groups). The error is e_i = R_i - predicted R_i, so the predicted return is R_i - e_i.
Both axes are truncated at -30% and 60%; values outside are drawn on the edge.
The dashed line is "predicted = actual"; the closer the points are to it, the more accurate the prediction.
Run table5_prediction_errors.py R1 first.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES, OUTPUT_TABLES  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from figure_style import MINUS  # noqa: E402

LO, HI = -30.0, 60.0
MODELS = [  # (column of the per-deal error file, panel title)
    ("error_(1) 数値の情報のみ", "(a) 基本モデル"),
    ("error_(2) (1)＋感情指標", "(b) 語調モデル"),
    ("error_(3) (1)＋書類の取引条件", "(c) 取引条件モデル"),
]


def main():
    deals = pd.read_csv(OUTPUT_TABLES / "table5_prediction_errors_R1_by_deal.csv")
    actual = deals["actual_return_pct"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.8), sharex=True, sharey=True)
    ticks = [-30, 0, 20, 40, 60]
    labels = [f"{MINUS}30以下", "0", "20", "40", "60以上"]
    for ax, (column, title) in zip(axes, MODELS):
        error = deals[column]
        predicted = actual - error
        mae = error.abs().mean()
        rmse = np.sqrt((error ** 2).mean())
        ax.axhline(0, color="0.85", lw=0.6, zorder=0)
        ax.axvline(0, color="0.85", lw=0.6, zorder=0)
        ax.plot([LO, HI], [LO, HI], ls="--", color="0.45", lw=0.9, zorder=1)
        ax.scatter(np.clip(actual, LO, HI), np.clip(predicted, LO, HI), marker="o", facecolors="none",
                   edgecolors="0.3", s=16, linewidths=0.7, zorder=2)
        ax.set_title(f"{title}\nMAE {mae:.2f}　RMSE {rmse:.2f}", fontsize=11)
        ax.set_xticks(ticks, labels)
        ax.set_yticks(ticks, labels)
        ax.set_xlim(LO - 3, HI + 3)
        ax.set_ylim(LO - 3, HI + 3)
        ax.set_xlabel(r"実際の収益率 $R_i$（%）")
    axes[0].set_ylabel(r"予測した収益率 $\hat{R}_i$（%）")
    fig.savefig(OUTPUT_FIGURES / "figure5_4_actual_and_predicted_returns.png")


if __name__ == "__main__":
    main()
