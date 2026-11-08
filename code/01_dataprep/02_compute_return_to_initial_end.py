"""Read the initial end date of the offer period and compute the return R_i (Section 3.3).

  return_to_initial_end_pct (R_i)
      100 x (close on E / close on J+1 - 1), where E is the last trading day on or
      before the initial end date of the offer period (extensions are ignored).
      The market is not subtracted (Hsieh and Walkling 2005); year dummies are
      used in the regressions instead.
  market_adjusted_return_to_initial_end_pct (robustness check)
      sum over J+2..E of (daily stock return - daily TOPIX ETF return), in %.

Inputs
  data/processed/price_gap.csv (01_compute_price_gap.py; J is taken from it)
  RAW_DATA/data*/prices*/{deal}.csv, index_topix_etf*.csv, tob_deals.csv, PDFs
  RAW_DATA/window_by_tob_end/targets_v2.csv (earlier computation, comparison only)
Output
  data/processed/return_to_initial_end.csv
"""
import os
import re
import sys
import unicodedata
from pathlib import Path

import fitz
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED, RAW_DATA  # noqa: E402

B = str(RAW_DATA) + "/"
PRICE_GAP = pd.read_csv(PROCESSED / "price_gap.csv", index_col=0)


def closes(*paths):
    """Read several price files into one date -> close dictionary (missing files are skipped)."""
    out = {}
    for p in paths:
        if os.path.exists(p):
            t = pd.read_csv(p, dtype=str)
            t["c"] = pd.to_numeric(t.close, errors="coerce")
            t = t.dropna(subset=["c"])
            out.update(zip(t.date.str[:10], t.c))
    return out


INDEX = {"2022_onward": closes(B + "data/index_topix_etf.csv"),
         "2019_2021": closes(B + "data_old/index_topix_etf_all.csv")}
NEW_DEALS = pd.read_csv(B + "data/tob_deals.csv", dtype=str, keep_default_na=False)
OLD_DEALS = pd.read_csv(B + "data_old/tob_deals.csv", dtype=str, keep_default_na=False)
OLD_DEALS = OLD_DEALS.assign(doc=lambda x: x.edinet_todokede.where(x.edinet_todokede != "", x.edinet_iken),
                             key=lambda x: x.target_code + "_" + x.first_date)
OLD_DOCUMENT = OLD_DEALS[OLD_DEALS.doc != ""].drop_duplicates("key").set_index("key").doc


def to_western_year(t):
    t = re.sub(r"令和(元|\d+)年",
               lambda g: f'{2018 + (1 if g.group(1) == "元" else int(g.group(1)))}年', t)
    return re.sub(r"平成(\d+)年", lambda g: f"{1988 + int(g.group(1))}年", t)


DATE = r"(\d{4})年(\d{1,2})月(\d{1,2})日(?:[(（][^)）]{1,4}[)）])?"   # date followed by the weekday in brackets


def initial_end_date(t):
    """Return (initial end date 'YYYY-MM-DD', evidence text) or (None, '').

    「届出当初の期間」 is read first so that the initial end date is used for extended offers."""
    for heading in [r"届出当初の期間", r"買付け等の期間"]:
        for h in re.finditer(heading, t):
            m = re.match(r".{0,60}?" + DATE + r"から" + DATE, t[h.end():h.end() + 200])
            if m:
                g = list(map(int, m.groups()[3:]))
                return f"{g[0]:04d}-{g[1]:02d}-{g[2]:02d}", t[h.start():h.end() + m.end()]
    return None, ""


rows = []
for deal_id, r in PRICE_GAP.iterrows():
    code, announcement_date = deal_id.split("_")
    group = "2022_onward" if announcement_date >= "2022" else "2019_2021"
    if group == "2022_onward":
        d = NEW_DEALS[(NEW_DEALS.target_code == code) & (NEW_DEALS.first_date == announcement_date) & (NEW_DEALS.status == "")]
        doc = d.edinet_todokede.iloc[0] if len(d) else ""
        pdf = B + f"data/edinet_pdf/{doc}.pdf"
        price = closes(B + f"data/prices/{deal_id}.csv", B + f"data/prices_ext/{deal_id}.csv")
    else:
        doc = OLD_DOCUMENT.get(deal_id, "")
        pdf = B + f"data_old/pdf/{doc}.pdf"
        price = closes(B + f"data_old/prices/{deal_id}.csv", B + f"data_old/prices_ext/{deal_id}.csv")
    out = {"deal_id": deal_id, "document_id": doc}
    if not doc or not os.path.exists(pdf):
        rows.append({**out, "reason_return_missing": "書類なし"})
        continue
    t = to_western_year(re.sub(r"\s+", "", unicodedata.normalize("NFKC", "".join(p.get_text() for p in fitz.open(pdf)))))
    end, evidence = initial_end_date(t)
    out.update(initial_offer_end_date=end, initial_offer_end_date_evidence=evidence[:120])
    index = INDEX[group]
    days = sorted(set(price) & set(index))
    J = str(r.first_trading_day_after_announcement)[:10]
    if not end:
        rows.append({**out, "reason_return_missing": "末日が読めない"})
        continue
    if J not in days:
        rows.append({**out, "reason_return_missing": "J が株価にない"})
        continue
    j = days.index(J)
    e = max([i for i, x in enumerate(days) if x <= end], default=-1)
    if days[-1] < end:
        rows.append({**out, "reason_return_missing": "末日まで株価がない"})
        continue
    if e < j + 2:
        rows.append({**out, "reason_return_missing": "末日が J+2 より前"})
        continue
    excess = [(price[days[i]] / price[days[i - 1]] - 1) - (index[days[i]] / index[days[i - 1]] - 1) for i in range(j + 2, e + 1)]
    market = [index[days[i]] / index[days[i - 1]] - 1 for i in range(j + 2, e + 1)]
    out.update({
        "return_to_initial_end_pct": 100 * round(price[days[e]] / price[days[j + 1]] - 1, 5),
        "market_adjusted_return_to_initial_end_pct": 100 * round(sum(excess), 5),
        "topix_return_to_initial_end_pct": 100 * round(sum(market), 5),
        "number_of_trading_days_in_return": len(excess),
        "initial_offer_end_trading_date": days[e],
        "reason_return_missing": "",
    })
    rows.append(out)
result = pd.DataFrame(rows).set_index("deal_id")
result.to_csv(PROCESSED / "return_to_initial_end.csv", encoding="utf-8-sig")
print("deals", len(result), "| return available", int(result.return_to_initial_end_pct.notna().sum()))
print(result.reason_return_missing.value_counts().to_string())

# comparison with the earlier computation of the market-adjusted return
earlier = pd.read_csv(B + "window_by_tob_end/targets_v2.csv", dtype={"code": str})
earlier.index = earlier.code + "_" + earlier.event_date
c = result.join(earlier[["W1_期间内", "label_end_W1"]]).dropna(subset=["market_adjusted_return_to_initial_end_pct", "W1_期间内"])
print("compared", len(c), "| market-adjusted return differs by > 0.01:",
      int(((c.market_adjusted_return_to_initial_end_pct - c.W1_期间内).abs() > 0.01).sum()),
      "| end date differs:", int((c.initial_offer_end_trading_date != c.label_end_W1).sum()))
