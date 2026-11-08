"""Differences by market attention (Chapter 5, attention).

Dependent variable: y = 100 x ln(1 + R_i / 100), as in table5_regressions.py (with year dummies).
Sample: the 403 deals of the analysis sample.

  (1) Nikkei news after the announcement (yes / no):
      mean absolute residual of y on the price gap and the partial offer dummy, and the effect
      of three deal terms estimated separately in each group (HC1 standard errors)
  (2) partial offers with a price gap above 2%: mean y for low / high composite attention
  (3) offer premium (% of the close before the announcement) and normal trading value:
      median (quantile) regression of the premium on log trading value with controls,
      and median premiums by attention group, also with the premium measured against the
      close 60 trading days before the announcement

Inputs   data/processed/analysis_table.csv, data/processed/attention_measures.csv,
         RAW_DATA/data*/prices/{deal}.csv (for the 60-day premium)
Output   output/tables/table5_attention.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import GUIDELINE_DATE, OUTPUT_TABLES, PARTIAL_OFFER_GAP_THRESHOLD_PCT, PROCESSED, RAW_DATA  # noqa: E402
from sample import load_sample  # noqa: E402

warnings.filterwarnings("ignore")


def main():
    s = load_sample()
    s = s.join(pd.read_csv(PROCESSED / "attention_measures.csv", index_col=0)[
        ["nikkei_articles_after", "reported_before_announcement", "composite_attention_score", "log_normal_trading_value"]])
    s["y"] = 100 * np.log1p(s.return_to_initial_end_pct / 100)
    s["nikkei_news_after"] = s.nikkei_articles_after > 0
    years = pd.get_dummies(s.announcement_year.astype(str), prefix="year", drop_first=True).astype(float)
    rows = []

    def add(section, item, **values):
        rows.append({"section": section, "item": item, **values})
        print(section, item, values)

    x = sm.add_constant(s[["price_gap_at_start_pct", "term_partial_tender_offer"]].astype(float).join(years))
    s["absolute_residual"] = (s.y - sm.OLS(s.y, x).fit().predict(x)).abs()
    no, yes = s[~s.nikkei_news_after], s[s.nikkei_news_after]
    add("(1) 公表後の日経報道", "説明できない部分の絶対値の平均（報道なし／あり）",
        without_news=round(no.absolute_residual.mean(), 2), with_news=round(yes.absolute_residual.mean(), 2),
        p_value=round(stats.mannwhitneyu(yes.absolute_residual, no.absolute_residual).pvalue, 4),
        deals=f"{len(no)}/{len(yes)}")

    def effect(sub, term):
        x = sub[[term, "price_gap_at_start_pct", "term_partial_tender_offer"]].astype(float).join(
            pd.get_dummies(sub.announcement_year.astype(str), prefix="year", drop_first=True).astype(float))
        r = sm.OLS(sub.y, sm.add_constant(x)).fit(cov_type="HC1")
        return round(r.params[term], 2), round(r.pvalues[term], 3), int(x[term].sum())

    for term, label in [("term_competitive_bidding", "入札・競合あり"), ("term_resolves_parent_subsidiary_listing", "親子上場の解消"),
                        ("term_abolishes_shareholder_benefits", "株主優待の廃止")]:
        add("(1) 公表後の日経報道", f"{label}の効果（係数, p値, 該当件数）（報道なし／あり）",
            without_news=effect(no, term), with_news=effect(yes, term))

    g = PARTIAL_OFFER_GAP_THRESHOLD_PCT
    high = s[(s.term_partial_tender_offer == 1) & (s.price_gap_at_start_pct > g)]
    low_attention = high.composite_attention_score <= s.composite_attention_score.median()
    add("(2) 部分買付け", f"価格差{g:.0f}%超の収益（注目度 低／高）",
        low=round(high[low_attention].y.mean(), 2), high=round(high[~low_attention].y.mean(), 2),
        p_value=round(stats.ttest_ind(high[low_attention].y, high[~low_attention].y, equal_var=False).pvalue, 3),
        deals=f"{int(low_attention.sum())}/{int((~low_attention).sum())}",
        rank_correlation=round(stats.spearmanr(high.composite_attention_score, high.y)[0], 2))

    s["premium_pct"] = 100 * s.offer_premium_ratio
    s["after_guideline"] = s.announcement_date >= GUIDELINE_DATE
    for controls, label in [("log_market_capitalization", "時価総額"),
                            ("log_market_capitalization + term_investment_fund_involved_in_acquirer + term_management_buyout_without_fund", "時価総額・ファンド・MBO"),
                            ("log_market_capitalization + term_investment_fund_involved_in_acquirer + term_management_buyout_without_fund + term_partial_tender_offer",
                             "時価総額・ファンド・MBO・部分買付け")]:
        for sub, period in [(s, "全体"), (s[s.after_guideline], "指針後")]:
            r = smf.quantreg("premium_pct ~ log_normal_trading_value + " + controls,
                             sub.dropna(subset=["premium_pct", "log_normal_trading_value", "log_market_capitalization"])).fit(q=.5)
            add("(3) プレミアム", f"売買代金（対数）の係数｜統制：{label}｜{period}",
                coefficient=round(r.params["log_normal_trading_value"], 2),
                p_value=round(r.pvalues["log_normal_trading_value"], 3), deals=int(r.nobs))

    def premium_60_days_before(deal_id):
        """Premium against the close 60 trading days before the announcement (ratio); NaN if prices are missing.

        The offer price is recovered as close on the announcement day x (1 + premium)."""
        folder = "data" if deal_id[-10:] >= "2022" else "data_old"
        path = RAW_DATA / folder / "prices" / f"{deal_id}.csv"
        if not path.exists():
            return np.nan
        p = pd.read_csv(path)
        ix = p.index[p.date <= deal_id.split("_")[1]]
        if len(ix) <= 60:
            return np.nan
        c0, c60 = p.close.iloc[ix[-1]], p.close.iloc[ix[-1] - 60]
        return c0 * (1 + s.loc[deal_id, "offer_premium_ratio"]) / c60 - 1

    s["premium_60_days_before_pct"] = [100 * premium_60_days_before(k) for k in s.index]
    median_value = s.log_normal_trading_value.median()
    s["attention_group"] = np.where(s.reported_before_announcement == 1, "事前報道あり",
                                    np.where(s.log_normal_trading_value > median_value, "平常の売買代金 大", "平常の売買代金 小"))
    for group, d in s.groupby("attention_group"):
        add("(3) プレミアム", f"プレミアムの中央値（{group}）",
            premium_against_previous_close=round(d.premium_pct.median(), 1),
            premium_against_close_60_days_before=round(d.premium_60_days_before_pct.median(), 1), deals=len(d))
    nb = s[s.reported_before_announcement == 0]
    big, small = nb[nb.log_normal_trading_value > median_value], nb[nb.log_normal_trading_value <= median_value]
    add("(3) プレミアム", "売買代金 大／小（事前報道なし）の差の検定",
        p_value_previous_close=round(stats.mannwhitneyu(big.premium_pct, small.premium_pct).pvalue, 3),
        p_value_60_days_before=round(stats.mannwhitneyu(big.premium_60_days_before_pct.dropna(),
                                                        small.premium_60_days_before_pct.dropna()).pvalue, 3))
    pd.DataFrame(rows).to_csv(OUTPUT_TABLES / "table5_attention.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
