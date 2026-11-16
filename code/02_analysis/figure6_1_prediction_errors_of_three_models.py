"""Figure 6.1: MAE and RMSE of the three models (403 deals, grouped by target company into 10 groups).

Reads output/tables/table5_prediction_errors_R1.csv written by table5_prediction_errors.py (Table 5.2).

Output  output/figures/figure6_1_prediction_errors_of_three_models.png
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_FIGURES, OUTPUT_TABLES  # noqa: E402
import figure_style  # noqa: F401,E402

NAMES = ["基本モデル", "語調モデル", "取引条件モデル"]
COLORS = ["0.75", "0.55", "0.25"]


def main():
    t = pd.read_csv(OUTPUT_TABLES / "table5_prediction_errors_R1.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for ax, (col, title, top) in zip(axes, [("mean_absolute_error_pct", "MAE", 5), ("root_mean_squared_error_pct", "RMSE", 11)]):
        v = t[col].to_numpy()
        ax.bar(np.arange(3), v, color=COLORS, width=0.6)
        for x, val in enumerate(v):
            ax.text(x, val + top * 0.015, f"{val:.2f}", ha="center", va="bottom", fontsize=10)
        ax.set_xticks(np.arange(3), NAMES, fontsize=10)
        ax.set_ylim(0, top)
        ax.set_ylabel("予測誤差（%ポイント）")
        ax.set_title(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURES / "figure6_1_prediction_errors_of_three_models.png")
    print(t[["variable_set", "mean_absolute_error_pct", "root_mean_squared_error_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
