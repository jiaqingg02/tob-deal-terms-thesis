"""Out-of-sample prediction of the return and comparison of prediction errors (Section 4.3).

Question
  Do the deal terms read from the documents make the prediction of the return more accurate
  than a model that uses only the numbers available without reading the documents?

Evaluation (argument --evaluation)
  grouped (main)  The 403 deals of the analysis sample are split into 10 groups; deals of the
                  same company are always in the same group (sklearn GroupKFold). Each group is
                  predicted by a model trained on the other 9 groups, so every deal is predicted once.
  time (appendix) Half years 2024H1 - 2026H1 (prediction_utils.OUTER). For each period the model
                  is trained only on deals whose return period ended before the period starts,
                  excluding deals of the same company (221 evaluated deals).
  Settings of each method (METHODS) are chosen inside the training data only: with 5 groups by
  company (grouped) or with the time-ordered validation splits of prediction_utils.inner_splits (time).

Target: 100 x ln(1 + R_i / 100) (argument R1, default) or the market-adjusted return (W1).
Predictions are converted back to % return before the errors are computed.

Variable sets (the same variables as the right-hand side of the regression equation, equation.py;
no year dummies, no pinned dummy)
  (1) numbers only: max(S_i, 0), offer premium, TOPIX return before the announcement,
      log market capitalization, the two market listings, news before the announcement (yes / count),
      second or later offer for the same target, announcement in multiple stages.
      No deal term read from the documents.
  (2) (1) + dictionary-based sentiment scores
  (3) (1) + P_i, P_i max(S_i, 0) and the 10 other deal terms read from the documents

Method
  Step 1 (method selection, before looking at sets (2) and (3)): set (1) is predicted with each
  method in METHODS, and the method with the smallest mean absolute error (MAE) is used.
  Step 2: the three sets are predicted with the selected method.
  The relation between the variables and the return is not fixed to a straight line in advance:
  with random forests it is learned from the data (thresholds and combinations of variables).

Evaluation of the errors: mean absolute error and root mean squared error (in % return) and their
reduction from set (1), with 95% bootstrap intervals (5,000 resamples of deals, numpy default_rng(0);
the same resamples for both measures and all sets), and the Diebold-Mariano test (t-test of the mean
loss difference from set (1); absolute error for MAE, squared error for RMSE).

Outputs (suffix "" for grouped, "_time" for time)
  output/tables/table5_method_selection_{target}{suffix}.csv
  output/tables/table5_prediction_errors_{target}{suffix}.csv
  output/tables/table5_prediction_errors_{target}{suffix}_by_deal.csv
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prediction_utils  # noqa: E402
from config import OUTPUT_TABLES  # noqa: E402
from equation import DEAL_TERMS_EXCEPT_PARTIAL, PARTIAL_OFFER_TERMS, add_equation_columns  # noqa: E402
from sample import load_analysis_table, load_sample  # noqa: E402

warnings.filterwarnings("ignore")

NUMBERS_ONLY_VARIABLES = [
    "tender_payoff_pct", "offer_premium_ratio",
    "topix_return_before_announcement_ratio", "log_market_capitalization",
    "listed_on_prime_market", "listed_on_growth_market",
    "has_news_before_announcement", "news_count_before_announcement",
    "second_or_later_offer_for_same_target", "announced_in_multiple_stages",
]
SENTIMENT_VARIABLES = ["news_headline_tone", "news_headline_count", "opinion_statement_tone"]
DOCUMENT_VARIABLES = PARTIAL_OFFER_TERMS + DEAL_TERMS_EXCEPT_PARTIAL
VARIABLE_SETS = {
    "(1) 数値の情報のみ": NUMBERS_ONLY_VARIABLES,
    "(2) (1)＋感情指標": NUMBERS_ONLY_VARIABLES + SENTIMENT_VARIABLES,
    "(3) (1)＋書類の取引条件": NUMBERS_ONLY_VARIABLES + DOCUMENT_VARIABLES,
}
# Variables scaled with the robust scaler when the preprocessing "robust" is chosen (linear methods).
# The added variables are treated in the same way, except STANDARDIZED_ONLY_VARIABLES.
CONTINUOUS_VARIABLES = ["offer_premium_ratio", "topix_return_before_announcement_ratio",
                        "log_market_capitalization", "news_count_before_announcement",
                        "tender_payoff_pct"]
# 交差項は大半が0で四分位範囲が0になるため、頑健な尺度化ではなく標準化を当てる
STANDARDIZED_ONLY_VARIABLES = ["partial_x_tender_payoff_pct"]

# name -> candidate settings (preprocessing, function returning an unfitted model).
# The candidates are fixed in advance; random seeds are 0. Tree methods do not depend on the
# scale of the variables, so only the preprocessing "standard" (median imputation) is used.
LINEAR_PREPROCESSING = ["standard", "robust"]
METHODS = {
    "最小二乗法": [(p, lambda: LinearRegression()) for p in LINEAR_PREPROCESSING],
    "リッジ回帰": [(p, lambda a=a: Ridge(alpha=a)) for p in LINEAR_PREPROCESSING for a in (1, 10, 100)],
    "ラッソ回帰": [(p, lambda a=a: Lasso(alpha=a, max_iter=50000)) for p in LINEAR_PREPROCESSING for a in (0.1, 0.3, 1)],
    "エラスティックネット": [(p, lambda a=a: ElasticNet(alpha=a, l1_ratio=0.5, max_iter=50000))
                    for p in LINEAR_PREPROCESSING for a in (0.1, 0.3, 1)],
    "ランダムフォレスト": [("standard", lambda m=m: RandomForestRegressor(
        n_estimators=500, min_samples_leaf=m, max_features=0.5, random_state=0, n_jobs=-1)) for m in (5, 10, 20)],
    "勾配ブースティング": [("standard", lambda k=k: GradientBoostingRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=k, subsample=0.8, random_state=0)) for k in (1, 2, 3)],
}
N_GROUPS, N_INNER_GROUPS = 10, 5
N_BOOTSTRAP = 5000


def prepare(target: str) -> pd.DataFrame:
    d = load_analysis_table()
    d = d[(d.excluded_by_filing_rule == 0) & (d.document_availability_at_return_start == "ok")].copy()
    d = add_equation_columns(d)
    column = "return_to_initial_end_pct" if target == "R1" else "market_adjusted_return_to_initial_end_pct"
    d["return_raw"] = d[column]
    d["return_period_end"] = d["initial_offer_end_trading_date"].astype(str)
    d = d[d.return_raw.notna() & d.return_period_end.str.len().eq(10)]
    d["return_log"] = 100 * np.log1p(d.return_raw / 100)
    d["first_trading_day_after_announcement"] = d.first_trading_day_after_announcement.astype(str).str[:10]
    return d


def grouped_splits(data, n_groups):
    groups = data.target_securities_code
    return [(data.iloc[a], data.iloc[b])
            for a, b in GroupKFold(n_splits=n_groups).split(np.arange(len(data)), groups=groups)]


def make_folds(d, evaluation):
    """List of (training data, evaluation data, validation splits inside the training data)."""
    if evaluation == "grouped":
        d = d[d.index.isin(load_sample().index)]
        folds = []
        for train, test in grouped_splits(d, N_GROUPS):
            assert not set(train.target_securities_code) & set(test.target_securities_code)
            folds.append((train, test, grouped_splits(train, N_INNER_GROUPS)))
        return folds
    folds = []
    for _, start, end in prediction_utils.OUTER:
        test = d[d.first_trading_day_after_announcement.ge(start) & d.first_trading_day_after_announcement.lt(end)]
        train = d[d.return_period_end.lt(start) & ~d.target_securities_code.isin(test.target_securities_code)]
        if len(train) < prediction_utils.MIN_TRAIN or len(test) < prediction_utils.MIN_TEST:
            continue
        inner = prediction_utils.inner_splits(train, "return_period_end")
        if inner:
            folds.append((train, test, inner))
    return folds


def fit(train, variables, candidate):
    preprocessing, make_model = candidate
    continuous = CONTINUOUS_VARIABLES + [x for x in variables
                                         if x not in NUMBERS_ONLY_VARIABLES and x not in STANDARDIZED_ONLY_VARIABLES]
    prep = prediction_utils.Prep(variables, [], preprocessing, continuous).fit(train)
    model = make_model().fit(prep.transform(train), train.return_log.to_numpy())
    return prep, model


def prediction_errors(folds, variables, candidates):
    """Prediction error (actual minus predicted, % return) of every evaluated deal."""
    errors = {}
    for train, test, inner in folds:
        scores = []
        for candidate in candidates:   # choose the setting with the smallest squared error in validation
            residuals = []
            for x, v in inner:
                prep, model = fit(x, variables, candidate)
                residuals.append(model.predict(prep.transform(v)) - v.return_log.to_numpy())
            scores.append(np.mean(np.concatenate(residuals) ** 2))
        prep, model = fit(train, variables, candidates[int(np.argmin(scores))])
        predicted = 100 * np.expm1(model.predict(prep.transform(test)) / 100)
        errors.update(dict(zip(test.index, test.return_raw.to_numpy() - predicted)))
    return pd.Series(errors)


MEASURES = {   # name -> (measure, loss of each deal for the Diebold-Mariano test)
    "mean_absolute_error": (lambda e: np.mean(np.abs(e)), np.abs),
    "root_mean_squared_error": (lambda e: np.sqrt(np.mean(e ** 2)), np.square),
}


def compare(errors: dict, base_name: str, resamples) -> pd.DataFrame:
    """MAE and RMSE of each set, and their reduction from base_name with interval and DM test."""
    rows = []
    for name, e in errors.items():
        row = {"variable_set": name}
        for measure, (f, loss) in MEASURES.items():
            row[f"{measure}_pct"] = round(f(e), 2)
            if name == base_name:
                continue
            base = errors[base_name]
            reduction = [f(base[i]) - f(e[i]) for i in resamples]
            lower, upper = np.percentile(reduction, (2.5, 97.5))
            row[f"{measure}_reduction_from_set_1_pct"] = round(f(base) - f(e), 2)
            row[f"{measure}_reduction_95pct_lower"] = round(lower, 2)
            row[f"{measure}_reduction_95pct_upper"] = round(upper, 2)
            row[f"{measure}_diebold_mariano_p"] = round(stats.ttest_1samp(loss(base) - loss(e), 0).pvalue, 4)
        row["evaluated_deals"] = len(e)
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_resamples(n):
    rng = np.random.default_rng(0)
    return [rng.integers(0, n, n) for _ in range(N_BOOTSTRAP)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="R1", choices=["R1", "W1"])
    parser.add_argument("--evaluation", default="grouped", choices=["grouped", "time"])
    args = parser.parse_args()
    suffix = "" if args.evaluation == "grouped" else "_time"
    d = prepare(args.target)
    folds = make_folds(d, args.evaluation)
    base_name = list(VARIABLE_SETS)[0]

    # Step 1: choose the method by the MAE of set (1)
    selection = []
    for method, candidates in METHODS.items():
        e = prediction_errors(folds, VARIABLE_SETS[base_name], candidates).to_numpy()
        selection.append({"method": method, **{f"{m}_pct": f(e) for m, (f, _) in MEASURES.items()}})
    selection = pd.DataFrame(selection)
    method = selection.loc[selection.mean_absolute_error_pct.idxmin(), "method"]   # before rounding
    selection = selection.round(2)
    selection.to_csv(OUTPUT_TABLES / f"table5_method_selection_{args.target}{suffix}.csv",
                     index=False, encoding="utf-8-sig")
    print(selection.to_string(index=False))
    print("selected method:", method)

    # Step 2: the three sets with the selected method
    errors = {name: prediction_errors(folds, variables, METHODS[method])
              for name, variables in VARIABLE_SETS.items()}
    deals = errors[base_name].index
    evaluated = pd.concat([test for _, test, _ in folds]).loc[deals]
    errors = {name: e.reindex(deals).to_numpy() for name, e in errors.items()}

    pd.DataFrame({"deal_id": deals, "actual_return_pct": evaluated.return_raw.to_numpy(),
                  **{f"error_{name}": e for name, e in errors.items()}}).to_csv(
        OUTPUT_TABLES / f"table5_prediction_errors_{args.target}{suffix}_by_deal.csv",
        index=False, encoding="utf-8-sig")
    summary = compare(errors, base_name, bootstrap_resamples(len(deals)))
    summary.insert(0, "method", method)
    summary.to_csv(OUTPUT_TABLES / f"table5_prediction_errors_{args.target}{suffix}.csv",
                   index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    print(f"target {args.target} | evaluation {args.evaluation} | evaluated deals {len(deals)}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
