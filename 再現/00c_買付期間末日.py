# 当初の買付期間の末日と、J+2〜その末日の超過収益（W1）を原文から計算する。延長は見ない（公表時に分かる末日だけを使う）
#   原文：2022年以降＝公開買付届出書（data/edinet_pdf）、2019・2021年＝公開買付けの開始の適時開示（data_old/pdf）。00a と同じ書類
#   末日の読み方：「届出当初の期間」があればその「〜から〜まで」の後ろの日付、なければ「買付け等の期間」の直後の「〜から〜まで」の後ろの日付
#   W1 ＝ 100 × Σ_{t=J+2}^{末日以前の最後の営業日} AR_t。J・AR の定義は 00a と同じ（株価は prices に加えて prices_ext も使う。
#   prices_ext は末日まで株価が足りない案件だけ IR BANK から1ページ取り直したもの：2022年以降は window_by_tob_end/fetch_ext.py、2019・2021年は 2026-10-30 に同じ方法で取得）
#   末日まで株価がない案件は W1 を空欄にする
#   R1 ＝ J+2〜末日の株価そのものの保有収益（%、日次収益の連乘、市場を引かない）。Hsieh and Walkling (2005) の arbitrage return と同じく市場を引かず、
#        時期の違いは回帰の年ダミーで統制する。公表後の対象会社株は市場とほぼ連動しない（Mitchell and Pulvino 2001：β≈0）ため、TOPIX を引くと市場の上昇がそのまま負の超過収益になる
#   mkt_W1 ＝ 同じ期間の TOPIX（ETF 1306）の日次上昇率の合計（%）。確認用
import re, unicodedata, fitz, numpy as np, pandas as pd, os
B = '../'; H = B + '再現/'
R0 = pd.read_csv(H + '中間/収益と価格差.csv', index_col=0)   # J（jump_day）は 00a の値をそのまま使う
def closes(*ps):
    out = {}
    for p in ps:
        if os.path.exists(p):
            t = pd.read_csv(p, dtype=str); t['c'] = pd.to_numeric(t.close, errors='coerce'); t = t.dropna(subset=['c']); out.update(zip(t.date.str[:10], t.c))
    return out
IDX = {'new': closes(B + 'data/index_topix_etf.csv'), 'old': closes(B + 'data_old/index_topix_etf_all.csv')}
ND = pd.read_csv(B + 'data/tob_deals.csv', dtype=str, keep_default_na=False)
OD = pd.read_csv(B + 'data_old/tob_deals.csv', dtype=str, keep_default_na=False)
OD = OD.assign(doc=lambda x: x.edinet_todokede.where(x.edinet_todokede != '', x.edinet_iken), key=lambda x: x.target_code + '_' + x.first_date)
OD = OD[OD.doc != ''].drop_duplicates('key').set_index('key').doc
def seireki(t):
    t = re.sub(r'令和(元|\d+)年', lambda g: f'{2018 + (1 if g.group(1) == "元" else int(g.group(1)))}年', t)
    return re.sub(r'平成(\d+)年', lambda g: f'{1988 + int(g.group(1))}年', t)
D2 = r'(\d{4})年(\d{1,2})月(\d{1,2})日(?:[(（][^)）]{1,4}[)）])?'
def enddate(t):
    for pat in [r'届出当初の期間', r'買付け等の期間']:
        for h in re.finditer(pat, t):
            m = re.match(r'.{0,60}?' + D2 + r'から' + D2, t[h.end():h.end() + 200])
            if m: g = list(map(int, m.groups()[3:])); return f'{g[0]:04d}-{g[1]:02d}-{g[2]:02d}', t[h.start():h.end() + m.end()]
    return None, ''
rows = []
for k, r in R0.iterrows():
    code, fd = k.split('_'); g = 'new' if fd >= '2022' else 'old'
    if g == 'new':
        d = ND[(ND.target_code == code) & (ND.first_date == fd) & (ND.status == '')]; doc = d.edinet_todokede.iloc[0] if len(d) else ''; f = B + f'data/edinet_pdf/{doc}.pdf'
        P = closes(B + f'data/prices/{k}.csv', B + f'data/prices_ext/{k}.csv')
    else:
        doc = OD.get(k, ''); f = B + f'data_old/pdf/{doc}.pdf'; P = closes(B + f'data_old/prices/{k}.csv', B + f'data_old/prices_ext/{k}.csv')
    o = {'key': k, '書類': doc}
    if not doc or not os.path.exists(f): o['理由'] = '書類なし'; rows.append(o); continue
    t = seireki(re.sub(r'\s+', '', unicodedata.normalize('NFKC', ''.join(p.get_text() for p in fitz.open(f)))))
    end, src = enddate(t); o['末日'] = end; o['根拠'] = src[:120]
    I = IDX[g]; days = sorted(set(P) & set(I)); J = str(r.jump_day)[:10]
    if not end: o['理由'] = '末日が読めない'; rows.append(o); continue
    if J not in days: o['理由'] = 'J が株価にない'; rows.append(o); continue
    j = days.index(J); kE = max([i for i, x in enumerate(days) if x <= end], default=-1)
    if days[-1] < end: o['理由'] = '末日まで株価がない'; rows.append(o); continue
    if kE < j + 2: o['理由'] = '末日が J+2 より前'; rows.append(o); continue
    ar = [(P[days[i]] / P[days[i - 1]] - 1) - (I[days[i]] / I[days[i - 1]] - 1) for i in range(j + 2, kE + 1)]
    mk = [I[days[i]] / I[days[i - 1]] - 1 for i in range(j + 2, kE + 1)]   # 同じ日の TOPIX の上昇率の合計（回帰で同期の市場を統制するため）
    o.update({'W1_raw': 100 * round(sum(ar), 5), 'n_W1': len(ar), 'label_end_W1': days[kE], 'mkt_W1': 100 * round(sum(mk), 5),
              'R1_raw': 100 * round(P[days[kE]] / P[days[j + 1]] - 1, 5), '理由': ''})   # R1：株価そのものの保有収益（日次の連乘＝J+1 の終値から末日の終値まで。市場を引かない）
    rows.append(o)
W = pd.DataFrame(rows).set_index('key'); W.to_csv(H + '中間/買付期間末日.csv', encoding='utf-8-sig')
print('件数', len(W), '｜W1 あり', W.W1_raw.notna().sum()); print(W.理由.value_counts().to_string())
print('2019・2021年', W[W.index.str[-10:] < '2022'].W1_raw.notna().sum(), '/', (W.index.str[-10:] < '2022').sum())
# 以前の計算（window_by_tob_end/targets_v2.csv、2022年以降）と照合
T = pd.read_csv(B + 'window_by_tob_end/targets_v2.csv', dtype={'code': str}); T.index = T.code + '_' + T.event_date
c = W.join(T[['W1_期间内', 'label_end_W1']], rsuffix='_旧').dropna(subset=['W1_raw', 'W1_期间内'])
print('照合', len(c), '件｜W1 の差>0.01', int(((c.W1_raw - c.W1_期间内).abs() > 0.01).sum()), '｜末日の違い', int((c.label_end_W1 != c.label_end_W1_旧).sum()))
