"""Out-of-sample prediction of the return and comparison of prediction errors (Section 4.3).

Design
  Evaluation periods: half years 2024H1 - 2026H1 (prediction_utils.OUTER). For each period,
  the model is trained only on deals whose return period ended before the period starts,
  excluding deals of the same company, so no future information is used.
  Target: 100 x ln(1 + R_i / 100) (argument R1, default) or the market-adjusted return (W1).
  Starting point of the prediction ("anchor"): 100 x ln(1 + max(price gap, 0)); for set (3)
  the anchor is 0 for partial offers, because only for full offers does the institution
  imply that the stock price moves toward the offer price. The model learns the deviation
  of the return from the anchor with Ridge regression; preprocessing and penalty are chosen
  within the training data only (prediction_utils.inner_splits).

Variable sets
  (1) market and stock price information only
  (2) (1) + dictionary-based sentiment scores
  (3) (1) + all deal terms read from the documents

Evaluation: mean absolute error (in % return) and its difference from set (1), with a 95%
bootstrap interval (5,000 resamples of deals).

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
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prediction_utils  # noqa: E402
from config import OUTPUT_TABLES  # noqa: E402
from sample import load_analysis_table  # noqa: E402

warnings.filterwarnings("ignore")

MARKET_AND_PRICE_VARIABLES = [
    "offer_premium_ratio", "board_supports_and_recommends_tender", "board_opposes_or_reserves_opinion",
    "second_or_later_offer_for_same_target", "announced_in_multiple_stages",
    "has_news_before_announcement", "news_count_before_announcement",
    "topix_return_before_announcement_ratio", "log_market_capitalization",
    "listed_on_prime_market", "listed_on_growth_market",
    "term_acquirer_is_investment_fund", "term_management_buyout",
    "price_gap_at_start_ratio", "pinned_to_offer_price",
]
CONTINUOUS_VARIABLES = ["offer_premium_ratio", "topix_return_before_announcement_ratio",
                        "log_market_capitalization", "news_count_before_announcement",
                        "price_gap_at_start_ratio"]
SENTIMENT_VARIABLES = ["news_headline_tone", "news_headline_count", "opinion_statement_tone"]
DEAL_TERM_VARIABLES = [
    "term_competitive_bidding", "term_no_price_increase_in_negotiation",
    "term_no_tender_agreement_with_major_shareholder", "term_board_opinion_is_neutral",
    "term_pending_regulatory_approval", "term_financed_by_own_funds",
    "term_abolishes_shareholder_benefits", "term_resolves_parent_subsidiary_listing",
]
VARIABLE_SETS = {  # name -> (variables, anchor is 0 for partial offers)
    "(1) 市場・株価の情報": (MARKET_AND_PRICE_VARIABLES, False),
    "(2) (1)＋感情指標": (MARKET_AND_PRICE_VARIABLES + SENTIMENT_VARIABLES, False),
    "(3) (1)＋書類の取引条件": (MARKET_AND_PRICE_VARIABLES + DEAL_TERM_VARIABLES, True),
}
CANDIDATES = [["standard", 1], ["standard", 10], ["standard", 100],
              ["robust", 1], ["robust", 10], ["robust", 100]]   # (preprocessing, Ridge penalty)


def prepare(target: str) -> pd.DataFrame:
    d = load_analysis_table()
    d = d[(d.excluded_by_filing_rule == 0) & (d.document_availability_at_return_start == "ok")].copy()
    d["term_partial_tender_offer"] = d["term_partial_tender_offer"].fillna(0)
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


def anchor(x, zero_for_partial):
    v = 100 * np.log1p(x.price_gap_at_start_ratio.fillna(0).clip(lower=0).to_numpy())
    return v * (1 - x.term_partial_tender_offer.to_numpy()) if zero_for_partial else v


def fit(train, variables, zero_for_partial, candidate):
    continuous = CONTINUOUS_VARIABLES + [x for x in variables if x not in MARKET_AND_PRICE_VARIABLES]
    prep = prediction_utils.Prep(variables, [], candidate[0], continuous).fit(train)
    model = Ridge(alpha=candidate[1]).fit(prep.transform(train),
                                          train.return_log.to_numpy() - anchor(train, zero_for_partial))
    return prep, model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="R1", choices=["R1", "W1"])
    target = parser.parse_args().target
    d = prepare(target)

    records = []
    for period, train, test, inner in make_folds(d):
        for name, (variables, zero_for_partial) in VARIABLE_SETS.items():
            def predict(x, v, c):
                prep, model = fit(x, variables, zero_for_partial, c)
                return model.predict(prep.transform(v)) + anchor(v, zero_for_partial)
            # choose the candidate with the smallest squared error in the validation splits,
            # refit on the whole training data and predict the evaluation period
            scores = [np.mean(np.concatenate([predict(x, v, c) - v.return_log.to_numpy() for x, v in inner if len(v)]) ** 2)
                      for c in CANDIDATES]
            best = CANDIDATES[int(np.argmin(scores))]
            prep, model = fit(train, variables, zero_for_partial, best)
            pred = model.predict(prep.transform(test)) + anchor(test, zero_for_partial)
            for k, p in zip(test.index, pred):
                records.append({"variable_set": name, "evaluation_period": period, "deal_id": k,
                                "actual_return_pct": test.loc[k, "return_raw"],
                                "predicted_return_pct": 100 * np.expm1(p / 100),
                                "training_deals": len(train)})
    by_deal = pd.DataFrame(records)
    by_deal["absolute_error_pct"] = (by_deal.actual_return_pct - by_deal.predicted_return_pct).abs()
    by_deal.to_csv(OUTPUT_TABLES / f"table5_prediction_errors_{target}_by_deal.csv", index=False, encoding="utf-8-sig")

    rng = np.random.default_rng(0)

    def interval(x):
        x = np.asarray(x)
        boot = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(5000)]
        return np.round(np.percentile(boot, (2.5, 97.5)), 2)

    base = by_deal[by_deal.variable_set == list(VARIABLE_SETS)[0]].set_index("deal_id")
    print(f"target {target} | evaluated deals {len(base)} | training deals by period",
          by_deal.groupby("evaluation_period").training_deals.first().to_dict())
    rows = []
    for name in VARIABLE_SETS:
        e = by_deal[by_deal.variable_set == name].set_index("deal_id").reindex(base.index)
        diff = base.absolute_error_pct - e.absolute_error_pct
        lo, hi = interval(diff)
        rows.append({"variable_set": name, "mean_absolute_error_pct": round(e.absolute_error_pct.mean(), 2),
                     "reduction_from_set_1_pct": round(diff.mean(), 2),
                     "reduction_95pct_lower": lo, "reduction_95pct_upper": hi,
                     "evaluated_deals": len(e)})
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_TABLES / f"table5_prediction_errors_{target}.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
