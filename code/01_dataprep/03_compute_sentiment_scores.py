"""Compute the dictionary-based sentiment scores used in the prediction comparison (Section 4.3).

  news_headline_tone     (positive - negative) / (positive + negative) words in the
                         Kabutan headlines of the 30 days before the announcement (-1..1)
  news_headline_count    number of those headlines
  opinion_statement_tone the same score for the section 「意見の内容、根拠及び理由」
                         of the target's opinion statement

Inputs
  data/inputs/prepared_data_corrected.csv, prepared_old.csv (deal lists)
  data/inputs/traditional_sentiment_旧.csv, traditional_sentiment_old.csv (earlier values, comparison only)
  RAW_DATA/data*/news_windows/{deal}.csv, RAW_DATA/data/edinet_pdf/, RAW_DATA/data_old/text/
Output
  data/processed/sentiment_scores.csv
"""
import os
import re
import sys
import unicodedata
from pathlib import Path

import fitz
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INPUTS, PROCESSED, RAW_DATA  # noqa: E402

B = str(RAW_DATA) + "/"
NEWS_POSITIVE = "上方修正 増益 最高益 増配 好調 上昇 高値 急騰 続伸 反発 黒字 受注 提携 ストップ高 増収 復配 好感 上振れ".split()
NEWS_NEGATIVE = "下方修正 減益 赤字 減配 無配 不振 下落 安値 急落 続落 反落 損失 減収 ストップ安 懸念 不祥事 訴訟 下振れ 特損 債務超過".split()
OPINION_POSITIVE = "賛同 推奨 妥当 公正 相当 合理的 向上 シナジー 成長".split()
OPINION_NEGATIVE = "反対 留保 不十分 困難 懸念 リスク 不利益 損失 毀損".split()


def tone(text, positive, negative):
    p = sum(text.count(w) for w in positive)
    n = sum(text.count(w) for w in negative)
    return (p - n) / (p + n) if p + n else 0.0


def news(path):
    """(headline tone, headline count) for one deal; (0, 0) if there is no headline file."""
    if not os.path.exists(path):
        return 0.0, 0
    x = pd.read_csv(path)
    return tone(unicodedata.normalize("NFKC", " ".join(x.title.astype(str))), NEWS_POSITIVE, NEWS_NEGATIVE), len(x)


rows = []
new = pd.read_csv(INPUTS / "prepared_data_corrected.csv", dtype={"code": str}, keep_default_na=False)
for r in new.itertuples():
    deal_id = f"{r.code}_{r.event_date}"
    o = {"deal_id": deal_id}
    o["news_headline_tone"], o["news_headline_count"] = news(f"{B}data/news_windows/{deal_id}.csv")
    pdf = f"{B}data/edinet_pdf/{r.edinet_iken}.pdf"
    o["opinion_statement_tone"] = np.nan
    if r.edinet_iken and os.path.exists(pdf):
        t = re.sub(r"\s+", "", unicodedata.normalize("NFKC", "".join(p.get_text() for p in fitz.open(pdf))))
        heads = [m.start() for m in re.finditer(r"【当該公開買付けに関する意見の内容、根拠及び理由】", t)]
        # if the heading appears more than once, use the text after the last one; without it, use the whole text
        o["opinion_statement_tone"] = tone(t[heads[-1]:] if heads else t, OPINION_POSITIVE, OPINION_NEGATIVE)
    rows.append(o)

old = pd.read_csv(INPUTS / "prepared_old.csv", dtype={"code": str}, keep_default_na=False)
old_deals = pd.read_csv(B + "data_old/tob_deals.csv", dtype=str, keep_default_na=False)
old_deals["key"] = old_deals.target_code + "_" + old_deals.first_date
old_deals = old_deals[old_deals.status == ""].set_index("key")
for r in old.itertuples():
    deal_id = f"{r.code}_{r.event_date}"
    o = {"deal_id": deal_id}
    o["news_headline_tone"], o["news_headline_count"] = news(f"{B}data_old/news_windows/{deal_id}.csv")
    doc = old_deals.loc[deal_id, "edinet_iken"] if deal_id in old_deals.index else ""
    path = f"{B}data_old/text/{doc}.txt"
    o["opinion_statement_tone"] = np.nan
    if doc and os.path.exists(path):
        t = re.sub(r"\s+", "", unicodedata.normalize("NFKC", open(path, encoding="utf-8", errors="ignore").read()))
        m = re.search(r"[0-9]\.(?:本公開買付け|当該公開買付け)に関する意見の内容、根拠及び理由", t)
        o["opinion_statement_tone"] = tone(t[m.start():] if m else t, OPINION_POSITIVE, OPINION_NEGATIVE)
    rows.append(o)
result = pd.DataFrame(rows).drop_duplicates("deal_id").set_index("deal_id")
result.to_csv(PROCESSED / "sentiment_scores.csv", encoding="utf-8-sig")

earlier = pd.concat([pd.read_csv(INPUTS / "traditional_sentiment_旧.csv"),
                     pd.read_csv(INPUTS / "traditional_sentiment_old.csv")]).drop_duplicates("key").set_index("key")
earlier = earlier.rename(columns={"新闻标题语气": "news_headline_tone", "新闻标题数": "news_headline_count",
                                  "意見表明語気": "opinion_statement_tone"})
for c in ["news_headline_tone", "news_headline_count", "opinion_statement_tone"]:
    a, b = result[c].reindex(earlier.index), earlier[c]
    ok = a.notna() & b.notna()
    print(f"{c}: compared {int(ok.sum())}, equal {int(np.isclose(a[ok], b[ok], atol=1e-9).sum())}, "
          f"max difference {float((a[ok] - b[ok]).abs().max()):.4f}, missing in only one {int((a.isna() != b.isna()).sum())}")
