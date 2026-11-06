# 当初の買付期間の末日を原文から読み、J+2〜その末日の収益（主な目的変数 R1、確認用の W1）を計算する
#
# 目的：論文の主な目的変数 R1 を作る（02_回帰.py R1・03b_予測比較_条件.py R1 が読む）。
#       W1 は以前の主な設定で、現在は確認用である（02_回帰.py W1）。
# 入力：中間/収益と価格差.csv（00a。J の値をそのまま使う）、案件一覧（data/tob_deals.csv・data_old/tob_deals.csv）、
#       原文PDF（2022年以降は公開買付届出書 data/edinet_pdf/、2019・2021年は開始の公表の適時開示 data_old/pdf/。00a と同じ書類）、
#       株価（prices/ と prices_ext/）、TOPIX 連動ETF（1306）の日次終値、window_by_tob_end/targets_v2.csv（以前の計算。照合用）
#       prices_ext/ は、末日まで株価が足りない案件だけ IR BANK から1ページ取り直したものである
#       （2022年以降は window_by_tob_end/fetch_ext.py、2019・2021年は 2026-10-30 に同じ方法で取得）。
# 出力：中間/買付期間末日.csv。計算できなかった案件は「理由」列に理由を書く
# 処理の流れ：①原文から当初の買付期間の末日を読む ②J+2〜末日の R1・W1 を計算する ③以前の計算と照合する
#
# 定義（日付は、個別株と指数の両方に終値がある取引日だけを数える。P＝個別株の終値、I＝1306 の終値）
#   J＝公表後最初の取引日（00a で決めたもの）。J+1 は J の次の取引日である。
#   末日＝当初の買付期間の末日。延長は見ない（公表の時点で分かる末日だけを使う）。原文に「届出当初の期間」があれば
#      その「〜から〜まで」の後ろの日付、なければ「買付け等の期間」の直後の「〜から〜まで」の後ろの日付とする。
#      末日が取引日でなければ、その前の最後の取引日 E を使う（末日が取引日なら E＝末日）。
#   R1＝100 ×（P_E ÷ P_{J+1} − 1）。J+2〜E の日次収益を連続して掛け合わせた保有収益（%）であり、市場の収益は引かない。
#      Hsieh and Walkling (2005) の arbitrage return と同じ扱いで、時期の違いは回帰の年ダミーで統制する。
#      公表後の対象会社の株価は市場とほとんど連動しない（Mitchell and Pulvino 2001：β≈0）ため、TOPIX を引くと
#      市場の上昇がそのまま負の超過収益になってしまうからである。02_回帰.py で 100×ln(1＋R1/100) に変換する
#   AR_t＝日次の超過収益＝（P_t ÷ P_{t−1} − 1）−（I_t ÷ I_{t−1} − 1）（00a と同じ）
#   W1＝100 × Σ_{t＝J+2}^{E} AR_t。TOPIX を引いた超過収益の和で、確認用である
#   mkt_W1＝同じ期間の TOPIX の日次収益の和（%）。確認用で、現在の回帰では使わない
#   R1・W1・mkt_W1 は、以前の処理と同じく小数第5位で丸めてから100倍する。末日まで株価がない案件は空欄にする
import re, unicodedata, fitz, numpy as np, pandas as pd, os
B = '../'; H = B + '再現/'
R0 = pd.read_csv(H + '中間/収益と価格差.csv', index_col=0)   # J（jump_day）は 00a の値をそのまま使う
def closes(*ps):
    """複数の株価ファイルを読み、日付→終値の辞書にまとめる（終値が数値の行だけ。存在しないファイルは飛ばす）。"""
    out = {}
    for p in ps:
        if os.path.exists(p):
            t = pd.read_csv(p, dtype=str); t['c'] = pd.to_numeric(t.close, errors='coerce'); t = t.dropna(subset=['c']); out.update(zip(t.date.str[:10], t.c))
    return out
IDX = {'new': closes(B + 'data/index_topix_etf.csv'), 'old': closes(B + 'data_old/index_topix_etf_all.csv')}
ND = pd.read_csv(B + 'data/tob_deals.csv', dtype=str, keep_default_na=False)
OD = pd.read_csv(B + 'data_old/tob_deals.csv', dtype=str, keep_default_na=False)
OD = OD.assign(doc=lambda x: x.edinet_todokede.where(x.edinet_todokede != '', x.edinet_iken), key=lambda x: x.target_code + '_' + x.first_date)
OD = OD[OD.doc != ''].drop_duplicates('key').set_index('key').doc   # 2019・2021年の適時開示ID（開始の公表がなければ意見表明）
def seireki(t):   # 平成・令和の年を西暦に直す
    t = re.sub(r'令和(元|\d+)年', lambda g: f'{2018 + (1 if g.group(1) == "元" else int(g.group(1)))}年', t)
    return re.sub(r'平成(\d+)年', lambda g: f'{1988 + int(g.group(1))}年', t)
D2 = r'(\d{4})年(\d{1,2})月(\d{1,2})日(?:[(（][^)）]{1,4}[)）])?'   # 「YYYY年M月D日」と、続く曜日のかっこ書き
def enddate(t):
    """原文 t から当初の買付期間の末日を読み、(末日 'YYYY-MM-DD', 根拠の文字列) を返す。読めなければ (None, '')。

    期間を延長した案件でも当初の末日を読むため、「届出当初の期間」の記載があればそれを優先する。"""
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
    mk = [I[days[i]] / I[days[i - 1]] - 1 for i in range(j + 2, kE + 1)]   # 同じ日の TOPIX の日次収益（mkt_W1。確認用）
    o.update({'W1_raw': 100 * round(sum(ar), 5), 'n_W1': len(ar), 'label_end_W1': days[kE], 'mkt_W1': 100 * round(sum(mk), 5),
              'R1_raw': 100 * round(P[days[kE]] / P[days[j + 1]] - 1, 5), '理由': ''})   # R1：J+1 の終値から E の終値までの変化率（J+2〜E の日次収益の積と同じ。市場を引かない）
    rows.append(o)
W = pd.DataFrame(rows).set_index('key'); W.to_csv(H + '中間/買付期間末日.csv', encoding='utf-8-sig')
print('件数', len(W), '｜W1 あり', W.W1_raw.notna().sum()); print(W.理由.value_counts().to_string())
print('2019・2021年', W[W.index.str[-10:] < '2022'].W1_raw.notna().sum(), '/', (W.index.str[-10:] < '2022').sum())
# 以前の計算（window_by_tob_end/targets_v2.csv、2022年以降の案件だけ）と照合し、W1 と末日の違いを数える
T = pd.read_csv(B + 'window_by_tob_end/targets_v2.csv', dtype={'code': str}).rename(columns={'W1_期间内': 'W1_以前の計算'})   # 入力ファイルの列名は作成時の名前のため、読み込み直後に改める
T.index = T.code + '_' + T.event_date
c = W.join(T[['W1_以前の計算', 'label_end_W1']], rsuffix='_旧').dropna(subset=['W1_raw', 'W1_以前の計算'])
print('照合', len(c), '件｜W1 の差>0.01', int(((c.W1_raw - c.W1_以前の計算).abs() > 0.01).sum()), '｜末日の違い', int((c.label_end_W1 != c.label_end_W1_旧).sum()))
