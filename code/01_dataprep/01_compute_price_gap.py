"""Compute J, the offer premium and the price gap S_i for each deal (Section 3.3).

J is the first trading day after the announcement: the announcement day itself if
the announcement was made before 14:00, otherwise the next trading day (an
unknown time is treated as 14:00 or later). The return start date is J+1.

  price_gap_at_start_ratio = (offer price / f_i) / close on J+1 - 1
  offer_premium_ratio      = (offer price / f_i) / close on the day before J - 1

f_i converts the offer price written in the document to the share unit of the
price data (stock splits and consolidations). It is the ratio of the closing
price written in the document to the closing price in the price data on the
same day, snapped to the nearest simple split ratio.

Inputs
  data/inputs/標本413.csv                 deal ids read from the documents (413 deals)
  data/inputs/価格差_除外.csv             deals whose price gap cannot be computed, with the reason
  data/inputs/買付価格_確認メモ.csv        3 deals whose offer price or f_i was checked by hand
  data/inputs/買付価格修正.csv             offer prices corrected after checking the documents
  data/inputs/prepared_data_corrected.csv, prepared_old.csv  earlier values, used only for comparison
  RAW_DATA/data*/prices/{deal}.csv, index_topix_etf*.csv, tob_deals.csv, tob_announcements.csv, PDFs
Output
  data/processed/price_gap.csv
  data/processed/price_gap_comparison_with_earlier_values.csv
"""
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import fitz
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ANNOUNCEMENT_CUTOFF_HOUR, INPUTS, PINNED_THRESHOLD_PCT, PROCESSED, RAW_DATA  # noqa: E402

B = str(RAW_DATA) + "/"
DEAL_IDS = pd.read_csv(INPUTS / "標本413.csv").key


def closes(path):
    """Date -> closing price (rows whose close is numeric only)."""
    t = pd.read_csv(path, dtype=str)
    t["c"] = pd.to_numeric(t.close, errors="coerce")
    t = t.dropna(subset=["c"])
    return dict(zip(t.date.str[:10], t.c))


def announcement_times(path):
    """(announcement date, first 30 characters of the title) -> announcement time."""
    return {(r["date"], r["title"][:30]): r.get("pub_time", "")
            for r in csv.DictReader(open(path, encoding="utf-8-sig"))}


SOURCES = {
    group: dict(index=closes(B + f"{folder}/{index_file}"),
                times=announcement_times(B + f"{folder}/tob_announcements.csv"),
                deals=pd.read_csv(B + f"{folder}/tob_deals.csv", dtype=str, keep_default_na=False),
                folder=folder)
    for group, folder, index_file in [("2022_onward", "data", "index_topix_etf.csv"),
                                      ("2019_2021", "data_old", "index_topix_etf_all.csv")]
}
# 2019/2021 deals: TDnet document of the offer start (or of the opinion if there is no start announcement)
OLD_DOCUMENT = (SOURCES["2019_2021"]["deals"]
                .assign(doc=lambda x: x.edinet_todokede.where(x.edinet_todokede != "", x.edinet_iken)))
OLD_DOCUMENT = (OLD_DOCUMENT[OLD_DOCUMENT.doc != ""]
                .assign(key=lambda x: x.target_code + "_" + x.first_date)
                .drop_duplicates("key").set_index("key").doc)
# deal -> (offer price, f_i) recorded in 買付価格_確認メモ.csv (no closing price in the document,
# or characters that cannot be read). None means the value read from the document is used.
HAND_CHECKED = {"4492_2021-02-05": (None, 6.0), "7946_2021-03-08": (None, 5.0),
                "7597_2021-11-09": (2575.0, None)}
PRICE_GAP_EXCLUDED = pd.read_csv(INPUTS / "価格差_除外.csv", dtype=str).set_index("key").理由
SPLIT_RATIOS = np.array(sorted({p / q for p in range(1, 201) for q in range(1, 7)}
                               | {1 / n for n in range(1, 201)}))


def snap_to_split_ratio(ratio):
    """Ratio (price data close / document close) -> nearest simple split ratio 1/ratio, or None if off by 0.5% or more."""
    x = 1 / ratio
    c = SPLIT_RATIOS[np.abs(SPLIT_RATIOS / x - 1).argmin()]
    return float(c) if abs(c / x - 1) < 0.005 else None


def to_western_year(t):
    t = re.sub(r"令和(元|\d+)年",
               lambda g: f'{2018 + (1 if g.group(1) == "元" else int(g.group(1)))}年', t)
    return re.sub(r"平成(\d+)年", lambda g: f"{1988 + int(g.group(1))}年", t)


rows = []
for deal_id in DEAL_IDS:
    code, announcement_date = deal_id.split("_")
    group = "2022_onward" if announcement_date >= "2022" else "2019_2021"
    s = SOURCES[group]
    price = closes(B + f'{s["folder"]}/prices/{deal_id}.csv')
    index = s["index"]
    days = sorted(set(price) & set(index))

    # J: an unknown announcement time is treated as 14:00 or later
    d = s["deals"]
    d = d[(d.target_code == code) & (d.first_date == announcement_date) & (d.status == "")]
    time = s["times"].get((announcement_date, d.sample_title.iloc[0][:30]), "") if len(d) else ""
    hour = int(time[11:13]) if len(time) >= 13 else 99
    J = next(x for x in days if (x >= announcement_date if hour < ANNOUNCEMENT_CUTOFF_HOUR else x > announcement_date))
    j = days.index(J)

    # offer price written in the document (same reading as 07_check_offer_prices.py)
    doc = d.edinet_todokede.iloc[0] if group == "2022_onward" else OLD_DOCUMENT.get(deal_id, "")
    pdf = B + (f"data/edinet_pdf/{doc}.pdf" if group == "2022_onward" else f"data_old/pdf/{doc}.pdf")
    t = re.sub(r"\s+", "", unicodedata.normalize("NFKC", "".join(p.get_text() for p in fitz.open(pdf))))
    m = None
    if group == "2022_onward":   # registration statement: the 【買付け等の価格】 section
        h = t.find("【買付け等の価格】")
        seg = t[h:h + 600] if h >= 0 else ""
        m = (re.search(r"()(普通株式)[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円", seg)
             or re.search(r"()()1株(につき|当たり)[、,]?金?([0-9,]+)円", seg))
    else:                        # TDnet release: right after the heading 買付け等の価格
        m = re.search(r"買付け等の価格[(（]?[0-9①]?[)）]?()(普通株式|株券)[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円", t)
        for hh in ([] if m else re.finditer(r"買付け等の価格", t)):
            m = re.match(r".{0,80}?()(普通株式|株券)?[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円",
                         t[hh.end():hh.end() + 200])
            if m:
                break
    offer = float(m.group(4).replace(",", "")) if m else np.nan

    # share adjustment factor f_i
    evidence = []
    for mm in re.finditer(r"(\d{4})年(\d+)月(\d+)日[^。円]{0,80}?終値(は)?([0-9,.]+)円", to_western_year(t)):
        dt = f"{mm.group(1)}-{int(mm.group(2)):02d}-{int(mm.group(3)):02d}"
        x = float(mm.group(5).replace(",", "") or 0)
        if dt in price and x > 0:
            evidence.append((dt, price[dt] / x))
    near = [r for dt, r in evidence if dt in (days[j - 1], announcement_date)]
    votes = Counter(f for f in map(snap_to_split_ratio, near or [r for _, r in evidence]) if f)
    if votes:
        factor = votes.most_common(1)[0][0]
        basis = ("公表日前後の終値" if near else "原文中の終値") + f"（{sum(votes.values())}か所）"
    else:
        factor, basis = 1.0, "原文に終値の記載なし"
    if deal_id in HAND_CHECKED:
        offer = HAND_CHECKED[deal_id][0] or offer
        factor = HAND_CHECKED[deal_id][1] or factor
        basis = "data/inputs/買付価格_確認メモ.csv"
    adjusted_offer = offer / factor
    gap = adjusted_offer / price[days[j + 1]] - 1
    # J+1 must be the next market trading day; otherwise the stock did not trade on that day
    next_market_day = min(x for x in index if x > J)
    reason = "" if days[j + 1] == next_market_day else "J の翌営業日に売買がない"
    if deal_id in PRICE_GAP_EXCLUDED:
        reason = PRICE_GAP_EXCLUDED[deal_id]
    if reason:
        gap = np.nan
    rows.append({
        "deal_id": deal_id,
        "first_trading_day_after_announcement": J,
        "announcement_time": time,
        "offer_price_in_document": offer,
        "share_adjustment_factor": factor,
        "share_adjustment_factor_basis": basis,
        "close_on_day_before_first_trading_day": price[days[j - 1]],
        "close_on_return_start_date": price[days[j + 1]],
        "offer_premium_ratio": adjusted_offer / price[days[j - 1]] - 1,
        "price_gap_at_start_ratio": gap,
        "pinned_to_offer_price": float(abs(gap) <= PINNED_THRESHOLD_PCT / 100) if gap == gap else np.nan,
        "reason_price_gap_missing": reason,
    })
result = pd.DataFrame(rows).set_index("deal_id")
result.to_csv(PROCESSED / "price_gap.csv", encoding="utf-8-sig")

# ---- comparison with the values in the earlier input tables -------------------
earlier = pd.concat([pd.read_csv(INPUTS / "prepared_data_corrected.csv", dtype={"code": str}, keep_default_na=False),
                     pd.read_csv(INPUTS / "prepared_old.csv", dtype={"code": str}, keep_default_na=False)])
earlier = (earlier.assign(key=earlier.code + "_" + earlier.event_date)
           .drop_duplicates("key").set_index("key").loc[DEAL_IDS])
corrected = pd.read_csv(INPUTS / "買付価格修正.csv", dtype=str).set_index("key")
NOTE = {"6574_2023-05-12": "以前の表は株価データの丸め（5.0円）のため買付価格（調整後5.0円）と同じ値になりプレミアム0としていた。"
                           "原文の終値515円に対して買付価格500円で、正しくは−2.9%"}
comparison = []
for new_col, old_col in [("offer_premium_ratio", "premium"), ("price_gap_at_start_ratio", "spread_J1"),
                         ("pinned_to_offer_price", "pinned")]:
    old = pd.to_numeric(earlier[old_col], errors="coerce")
    new = result[new_col]
    same = ((new - old).abs() < 1e-4) | (new.isna() & old.isna())
    for k in result.index[~same]:
        comparison.append({"deal_id": k, "variable": new_col, "earlier_value": old[k], "recomputed_value": new[k],
                           "reason": "買付価格の誤りを修正（data/inputs/買付価格修正.csv）" if k in corrected.index else NOTE.get(k, "")})
comparison = pd.DataFrame(comparison, columns=["deal_id", "variable", "earlier_value", "recomputed_value", "reason"])
comparison.to_csv(PROCESSED / "price_gap_comparison_with_earlier_values.csv", index=False, encoding="utf-8-sig")
print("deals", len(result), "| J same as earlier", int((result.first_trading_day_after_announcement == earlier.jump_day.str[:10]).sum()),
      "| price gap available", int(result.price_gap_at_start_ratio.notna().sum()))
print("values that differ from the earlier tables:", len(comparison))
print(comparison.to_string())
