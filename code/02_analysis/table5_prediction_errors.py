"""Out-of-sample prediction of the return and comparison of prediction errors (Section 4.3).

Design
  Evaluation periods: half years 2024H1 - 2026H1 (prediction_utils.OUTER). For each period,
  the model is trained only on deals whose return period ended before the period starts,
  excluding deals of the same company, so no future information is used.
  Target: 100 x ln(1 + R_i / 100) (argument R1, default) or the market-adjusted return (W1).
  Model: Ridge regression on the right-hand side of the one equation of Section 4.1
  (equation.py), without year dummies (the years of the evaluation periods are not in the
  training data). No starting point ("anchor") is used: max(S_i, 0) is an explanatory
  variable. The three sets use the same method and differ only in the added variables.
  Preprocessing and penalty are chosen within the training data only (prediction_utils.inner_splits).
  交差項 P_i max(S_i, 0) は大半が0で四分位範囲が0になるため、頑健な尺度化ではなく標準化を当てる
  (STANDARDIZED_ONLY_VARIABLES)。以前の版はこの列を尺度化しておらず、結果が単位に依存していた。

Variable sets
  (1) numbers only: max(S_i, 0), pinned, offer premium, TOPIX return before the announcement,
      log market capitalization, the two market listings, news before the announcement (yes / count),
      second or later offer for the same target, announcement in multiple stages.
      No deal term read from the documents (fund, MBO, board opinion are not included).
  (2) (1) + dictionary-based sentiment scores
  (3) (1) + P_i, P_i max(S_i, 0) and the 10 other deal terms read from the documents

Simple rules for comparison (no model, the same evaluated deals):
  predicted return = max(S_i, 0)
  predicted return = max(S_i, 0), but 0 for partial offers
  (a deal with a missing price gap is predicted as 0 by both rules)

Evaluation: root mean squared error (main) and mean absolute error (in % return), and their
reduction from set (1), with 95% bootstrap intervals (5,000 resamples of deals,
numpy default_rng(0); the same resamples are used for both measures and all sets), and the
Diebold-Mariano test (t-test of the mean loss difference from set (1); squared error for the
root mean squared error, absolute error for the mean absolute error).

Outputs
  output/tables/table5_prediction_errors_{target}_by_deal.csv
  output/tables/table5_prediction_errors_{target}.csv
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prediction_utils  # noqa: E402
from config import OUTPUT_TABLES  # noqa: E402
from equation import DEAL_TERMS_EXCEPT_PARTIAL, PARTIAL_OFFER_TERMS, add_equation_columns  # noqa: E402
from sample import load_analysis_table  # noqa: E402

warnings.filterwarnings("ignore")

NUMBERS_ONLY_VARIABLES = [
    "tender_payoff_pct", "pinned", "offer_premium_ratio",
    "topix_return_before_announcement_ratio", "log_market_capitalization",
    "listed_on_prime_market", "listed_on_growth_market",
    "has_news_before_announcement", "news_count_before_announcement",
    "second_or_later_offer_for_same_target", "announced_in_multiple_stages",
]
SENTIMENT_VARIABLES = ["news_headline_tone", "news_headline_count", "opinion_statement_tone"]
VARIABLE_SETS = {
    "(1) 数値の情報のみ": NUMBERS_ONLY_VARIABLES,
    "(2) (1)＋感情指標": NUMBERS_ONLY_VARIABLES + SENTIMENT_VARIABLES,
    "(3) (1)＋書類の取引条件": NUMBERS_ONLY_VARIABLES + PARTIAL_OFFER_TERMS + DEAL_TERMS_EXCEPT_PARTIAL,
}
# Variables scaled with the robust scaler when the preprocessing "robust" is chosen. The variables
# added to set (1) (sentiment scores, deal terms) are treated in the same way, except
# STANDARDIZED_ONLY_VARIABLES.
CONTINUOUS_VARIABLES = ["offer_premium_ratio", "topix_return_before_announcement_ratio",
                        "log_market_capitalization", "news_count_before_announcement",
                        "tender_payoff_pct"]
# 交差項は大半が0で四分位範囲が0になるため、頑健な尺度化ではなく標準化を当てる
# (with an interquartile range of 0 the robust scaler leaves the variable unscaled, so the
# result would depend on its unit).
STANDARDIZED_ONLY_VARIABLES = ["partial_x_tender_payoff_pct"]
CANDIDATES = [["standard", 1], ["standard", 10], ["standard", 100],
              ["robust", 1], ["robust", 10], ["robust", 100]]   # (preprocessing, Ridge penalty)
N_BOOTSTRAP = 5000
SIMPLE_RULES = {   # name -> predicted return (%) from the evaluation data alone
    "単純な規則：予測値＝max(S,0)": lambda x: x.tender_payoff_pct.fillna(0),
    "単純な規則：予測値＝max(S,0)、ただし部分買付けは0":
        lambda x: x.tender_payoff_pct.fillna(0) * (1 - x.term_partial_tender_offer),
}


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


def make_folds(d):
    """(period, training data, evaluation data, validation splits inside the training data) for each period."""
    out = []
    for period, start, end in prediction_utils.OUTER:
        test = d[d.first_trading_day_after_announcement.ge(start) & d.first_trading_day_after_announcement.lt(end)]
        train = d[d.return_period_end.lt(start) & ~d.target_securities_code.isin(test.target_securities_code)]
        if len(train) < prediction_utils.MIN_TRAIN or len(test) < prediction_utils.MIN_TEST:
            continue
        splits = prediction_utils.inner_splits(train, "return_period_end")
        if splits:
            out.append((period, train, test, splits))
    return out


def fit(train, variables, candidate):
    continuous = CONTINUOUS_VARIABLES + [x for x in variables
                                         if x not in NUMBERS_ONLY_VARIABLES and x not in STANDARDIZED_ONLY_VARIABLES]
    prep = prediction_utils.Prep(variables, [], candidate[0], continuous).fit(train)
    model = Ridge(alpha=candidate[1]).fit(prep.transform(train), train.return_log.to_numpy())
    return prep, model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="R1", choices=["R1", "W1"])
    target = parser.parse_args().target
    d = prepare(target)

    records = []
    for period, train, test, inner in make_folds(d):
        for name, variables in VARIABLE_SETS.items():
            def predict(x, v, c):
                prep, model = fit(x, variables, c)
                return model.predict(prep.transform(v))
            # choose the candidate with the smallest squared error in the validation splits,
            # refit on the whole training data and predict the evaluation period
            scores = [np.mean(np.concatenate([predict(x, v, c) - v.return_log.to_numpy() for x, v in inner if len(v)]) ** 2)
                      for c in CANDIDATES]
            best = CANDIDATES[int(np.argmin(scores))]
            prep, model = fit(train, variables, best)
            pred = model.predict(prep.transform(test))
            for k, p in zip(test.index, pred):
                records.append({"variable_set": name, "evaluation_period": period, "deal_id": k,
                                "actual_return_pct": test.loc[k, "return_raw"],
                                "predicted_return_pct": 100 * np.expm1(p / 100),
                                "training_deals": len(train)})
        for name, rule in SIMPLE_RULES.items():
            for k, p in rule(test).items():
                records.append({"variable_set": name, "evaluation_period": period, "deal_id": k,
                                "actual_return_pct": test.loc[k, "return_raw"], "predicted_return_pct": p,
                                "training_deals": len(train)})
    by_deal = pd.DataFrame(records)
    by_deal["prediction_error_pct"] = by_deal.actual_return_pct - by_deal.predicted_return_pct
    by_deal["absolute_error_pct"] = by_deal.prediction_error_pct.abs()
    by_deal.to_csv(OUTPUT_TABLES / f"table5_prediction_errors_{target}_by_deal.csv", index=False, encoding="utf-8-sig")

    errors = {name: by_deal[by_deal.variable_set == name].set_index("deal_id").prediction_error_pct
              for name in [*VARIABLE_SETS, *SIMPLE_RULES]}
    base_name = list(VARIABLE_SETS)[0]
    deals = errors[base_name].index
    errors = {name: e.reindex(deals).to_numpy() for name, e in errors.items()}
    rng = np.random.default_rng(0)
    resamples = [rng.integers(0, len(deals), len(deals)) for _ in range(N_BOOTSTRAP)]
    measures = {"root_mean_squared_error": lambda e: np.sqrt(np.mean(e ** 2)),
                "mean_absolute_error": lambda e: np.mean(np.abs(e))}

    print(f"target {target} | evaluated deals {len(deals)} | training deals by period",
          by_deal.groupby("evaluation_period").training_deals.first().to_dict())
    rows = []
    for name in [*VARIABLE_SETS, *SIMPLE_RULES]:
        row = {"variable_set": name}
        for measure, f in measures.items():
            reduction = [f(errors[base_name][i]) - f(errors[name][i]) for i in resamples]
            lower, upper = np.percentile(reduction, (2.5, 97.5))
            row[f"{measure}_pct"] = round(f(errors[name]), 2)
            row[f"{measure}_reduction_from_set_1_pct"] = round(f(errors[base_name]) - f(errors[name]), 2)
            row[f"{measure}_reduction_95pct_lower"] = round(lower, 2)
            row[f"{measure}_reduction_95pct_upper"] = round(upper, 2)
            # Diebold-Mariano test: t-test that the mean loss difference (set (1) minus this set) is 0;
            # loss = squared error for the root mean squared error, absolute error for the mean absolute error
            loss = np.square if measure == "root_mean_squared_error" else np.abs
            difference = loss(errors[base_name]) - loss(errors[name])
            row[f"{measure}_diebold_mariano_p"] = (round(stats.ttest_1samp(difference, 0).pvalue, 4)
                                                   if name != base_name else np.nan)
        row["evaluated_deals"] = len(deals)
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_TABLES / f"table5_prediction_errors_{target}.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
