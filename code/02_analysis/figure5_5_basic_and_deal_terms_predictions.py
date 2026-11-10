"""Figure 5.5: Predicted returns of the basic model and the deal-terms model for the same deals (403 deals).

Reads the per-deal prediction errors written by table5_prediction_errors.py (R1, deals split by company
into 10 groups). The error is e_i = R_i - predicted R_i, so the predicted return is R_i - e_i.
Each deal appears twice at the same actual return: grey = basic model, blue = deal-terms model.
Both axes are truncated at -30% and 60%; values outside are drawn on the edge.
The dashed line is "predicted = actual".

Also writes output/tables/figure5_5_deals_whose_prediction_changed.csv: by full and partial offers, the number
of deals whose absolute error with the deal-terms model is smaller (larger) than with the basic model by
config.PREDICTION_CHANGE_HIGHLIGHT_PCT points or more, and the reduction of the absolute error.
Run table5_prediction_errors.py R1 first.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES, OUTPUT_TABLES, PREDICTION_CHANGE_HIGHLIGHT_PCT  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)
from figure_style import MINUS  # noqa: E402
from sample import load_sample  # noqa: E402

LO, HI = -30.0, 60.0
BASIC = "error_(1) 数値の情報のみ"
DEAL_TERMS = "error_(3) (1)＋書類の取引条件"


def main():
    deals = pd.read_csv(OUTPUT_TABLES / "table5_prediction_errors_R1_by_deal.csv")
    sample = load_sample().reset_index()
    deals = deals.merge(sample[["deal_id", "term_partial_tender_offer"]], on="deal_id", how="left",
                        validate="one_to_one")
    assert deals["term_partial_tender_offer"].notna().all()
    actual = deals["actual_return_pct"]

    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    ax.axhline(0, color="0.85", lw=0.6, zorder=0)
    ax.axvline(0, color="0.85", lw=0.6, zorder=0)
    ax.plot([LO, HI], [LO, HI], ls="--", color="0.45", lw=0.9, zorder=1)
    ax.scatter(np.clip(actual, LO, HI), np.clip(actual - deals[BASIC], LO, HI), color="0.7", s=14,
               linewidths=0, zorder=2, label="基本モデル")
    ax.scatter(np.clip(actual, LO, HI), np.clip(actual - deals[DEAL_TERMS], LO, HI), color="#1f5fbf", s=14,
               linewidths=0, zorder=3, label="取引条件モデル")
    ticks = [-30, 0, 20, 40, 60]
    labels = [f"{MINUS}30以下", "0", "20", "40", "60以上"]
    ax.set_xticks(ticks, labels)
    ax.set_yticks(ticks, labels)
    ax.set_xlim(LO - 3, HI + 3)
    ax.set_ylim(LO - 3, HI + 3)
    ax.set_xlabel(r"実際の収益率 $R_i$（%）")
    ax.set_ylabel(r"予測した収益率 $\hat{R}_i$（%）")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    fig.savefig(OUTPUT_FIGURES / "figure5_5_basic_and_deal_terms_predictions.png")

    reduction = deals[BASIC].abs() - deals[DEAL_TERMS].abs()
    rows = []
    for partial, label in [(0, "全部買付け"), (1, "部分買付け"), (None, "全体")]:
        mask = np.ones(len(deals), bool) if partial is None else (deals["term_partial_tender_offer"] == partial).to_numpy()
        rows.append({"案件": label, "件数": int(mask.sum()),
                     f"絶対誤差が{PREDICTION_CHANGE_HIGHLIGHT_PCT:g}ポイント以上縮んだ案件": int((reduction[mask] >= PREDICTION_CHANGE_HIGHLIGHT_PCT).sum()),
                     f"絶対誤差が{PREDICTION_CHANGE_HIGHLIGHT_PCT:g}ポイント以上広がった案件": int((reduction[mask] <= -PREDICTION_CHANGE_HIGHLIGHT_PCT).sum()),
                     "絶対誤差の減少の合計": round(reduction[mask].sum(), 2),
                     "絶対誤差の減少の1件あたり平均": round(reduction[mask].mean(), 2)})
    pd.DataFrame(rows).to_csv(OUTPUT_TABLES / "figure5_5_deals_whose_prediction_changed.csv", index=False,
                              encoding="utf-8-sig")


if __name__ == "__main__":
    main()
