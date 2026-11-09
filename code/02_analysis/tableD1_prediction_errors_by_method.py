"""Table D.1 (Appendix D): Prediction errors of the three variable sets with every method,
both evaluations and with or without the pinned dummy.

The main text uses the method selected in table5_prediction_errors.py (smallest MAE of set (1) in
the grouped evaluation). This program shows all other combinations, keeping everything else
identical (same deals, folds, target, variable sets, candidate settings, random seeds):
  methods      every method in table5_prediction_errors.METHODS
  evaluations  grouped (403 deals, 10 groups by company) and time (221 deals, half years 2024H1 - 2026H1)
  pinned dummy without (main) and with the dummy |S_i| <= 1% added to every set

For each combination: MAE and RMSE (% return) of each set, and for sets (2) and (3) the reduction
from set (1) with 95% bootstrap interval and Diebold-Mariano p-value (table5_prediction_errors.compare).

Output  output/tables/tableD1_prediction_errors_by_method.csv
"""
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_TABLES  # noqa: E402
from table5_prediction_errors import (METHODS, VARIABLE_SETS, bootstrap_resamples, compare,  # noqa: E402
                                      make_folds, prediction_errors, prepare)

warnings.filterwarnings("ignore")


def main():
    d = prepare("R1")
    base_name = list(VARIABLE_SETS)[0]
    tables = []
    for evaluation in ["grouped", "time"]:
        folds = make_folds(d, evaluation)
        for pinned in [False, True]:
            sets = {name: v + (["pinned"] if pinned else []) for name, v in VARIABLE_SETS.items()}
            for method, candidates in METHODS.items():
                errors = {name: prediction_errors(folds, v, candidates) for name, v in sets.items()}
                deals = errors[base_name].index
                errors = {name: e.reindex(deals).to_numpy() for name, e in errors.items()}
                table = compare(errors, base_name, bootstrap_resamples(len(deals)))
                table.insert(0, "method", method)
                table.insert(0, "pinned_dummy", "あり" if pinned else "なし")
                table.insert(0, "evaluation", "10グループ（403件）" if evaluation == "grouped" else "時間順（2024年以降）")
                tables.append(table)
                print(evaluation, "pinned" if pinned else "", method, "done", flush=True)
    result = pd.concat(tables, ignore_index=True)
    result.to_csv(OUTPUT_TABLES / "tableD1_prediction_errors_by_method.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 300)
    pd.set_option("display.max_rows", 200)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
