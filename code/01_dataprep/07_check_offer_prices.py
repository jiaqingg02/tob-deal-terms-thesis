"""Check, deal by deal, that the offer price used for the price gap equals the offer price
written in the original document (Section 3.3).

The offer price used in the analysis is recovered as close on J+1 x (1 + price gap).
A ratio different from 1 is accepted when it equals the share adjustment factor
(stock split or consolidation after the announcement). Three deals were checked
by hand (data/inputs/買付価格_確認メモ.csv).

Inputs   data/processed/analysis_table.csv, original PDFs, prices
Output   output/tables/offer_price_check.csv
"""
import re, unicodedata, fitz, numpy as np, pandas as pd, os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INPUTS, OUTPUT_TABLES, PROCESSED, RAW_DATA  # noqa: E402
B = str(RAW_DATA) + '/'
A = pd.read_csv(PROCESSED / 'analysis_table.csv', index_col=0, dtype={'target_securities_code': str})
A = A[A.price_gap_at_start_ratio.notna()]
OD = pd.read_csv(B + 'data_old/tob_deals.csv', dtype=str, keep_default_na=False); OD['doc'] = OD.edinet_todokede.where(OD.edinet_todokede != '', OD.edinet_iken)   # 2019・2021年の適時開示の書類ID（開始の公表がなければ意見表明の開示）
OD = OD[OD.doc != ''].assign(key=lambda x: x.target_code + '_' + x.first_date).drop_duplicates('key').set_index('key').doc
A['doc'] = [r.registration_statement_document_id if r.announcement_year >= 2022 else OD.get(k, '') for k, r in A.iterrows()]
rows = []
for k, r in A.iterrows():
    new = r.announcement_year >= 2022; px = pd.read_csv(B + (f'data/prices/{k}.csv' if new else f'data_old/prices/{k}.csv')).set_index('date').close.astype(float)
    i = list(px.index).index(r.first_trading_day_after_announcement[:10]) if r.first_trading_day_after_announcement[:10] in px.index else None
    close2 = px.iloc[i + 1] if i is not None and i + 1 < len(px) else np.nan   # J+1 の終値
    used = close2 * (1 + r.price_gap_at_start_ratio)
    t = unicodedata.normalize('NFKC', ''.join(p.get_text() for p in fitz.open(B + (f'data/edinet_pdf/{r.doc}.pdf' if new else f'data_old/pdf/{r.doc}.pdf'))))
    t = re.sub(r'\s+', '', t)
    m = None
    if new:   # 公開買付届出書：【買付け等の価格】の欄から、普通株式1株あたりの価格を読む
        j = t.find('【買付け等の価格】'); seg = t[j:j + 600] if j >= 0 else ''
        m = re.search(r'()(普通株式)[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円', seg) or re.search(r'()()1株(につき|当たり)[、,]?金?([0-9,]+)円', seg)
    else:     # 適時開示：「買付け等の価格」の見出しの直後を読む。本文中の提案価格などを拾わないよう、見出しから80字以内に限る
        m = re.search(r'買付け等の価格[(（]?[0-9①]?[)）]?()(普通株式|株券)[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円', t)   # まず「買付け等の価格 普通株式1株につき…」という見出しの形を探す
        if m: seg = t[m.start():m.start() + 120]
        for h in ([] if m else re.finditer(r'買付け等の価格', t)):
            m = re.match(r'.{0,80}?()(普通株式|株券)?[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円', t[h.end():h.end() + 200])
            if m: seg = t[h.end():h.end() + 120]; break
    doc = float(m.group(4).replace(',', '')) if m else np.nan
    # 株価データの調整係数：原文の「YYYY年M月D日の…終値X円」（平成・令和は西暦に直す）を探し、
    # 株価データの同じ日の終値との比をとる。株価データが後の株式分割・併合で調整されている場合に1から外れる
    tt = re.sub(r'平成(\d+)年', lambda g: f'{1988 + int(g.group(1))}年', re.sub(r'令和(元|\d+)年', lambda g: f'{2018 + (1 if g.group(1) == "元" else int(g.group(1)))}年', t))
    adj = np.nan
    for mm in re.finditer(r'(\d{4})年(\d+)月(\d+)日[^。]{0,80}?終値(は)?([0-9,.]+)円', tt):
        dt = f'{mm.group(1)}-{int(mm.group(2)):02d}-{int(mm.group(3)):02d}'
        if dt in px.index: adj = px[dt] / float(mm.group(5).replace(',', '')); break
    rows.append({'deal_id': k, 'offer_price_in_document': doc, 'offer_price_used_in_analysis': round(used, 1), 'ratio_used_to_document': round(used / doc, 4) if doc else np.nan, 'share_adjustment_factor_in_price_data': round(adj, 4), 'document_text': seg[:120]})
R = pd.DataFrame(rows); R['matches_within_1pct'] = (R.ratio_used_to_document - 1).abs() < 0.01
R['matches_after_share_adjustment'] = R.matches_within_1pct | ((R.ratio_used_to_document / R.share_adjustment_factor_in_price_data - 1).abs() < 0.02)
M = pd.read_csv(INPUTS / '買付価格_確認メモ.csv').set_index('案件')   # 原文に終値の記載がない、または文字が取り出せない3件を個別に確認した記録（理由つき）
R['checked_by_hand'] = R.deal_id.map(M.確認).fillna(''); R['confirmed'] = R.matches_after_share_adjustment | (R.checked_by_hand != '')
print('checked', len(R), '| read from document', int(R.offer_price_in_document.notna().sum()), '| within 1%', int(R.matches_within_1pct.sum()), '| match after share adjustment', int(R.matches_after_share_adjustment.sum()), '| confirmed incl. hand check', int(R.confirmed.sum()))
R.to_csv(OUTPUT_TABLES / 'offer_price_check.csv', index=False, encoding='utf-8-sig')
print(R[~R.matches_within_1pct].drop(columns='document_text').to_string())
