# 公表後最初の取引日 J・価格差・張り付き・プレミアムを、保存済みの株価と原文PDFから計算する
#
# 目的：回帰の説明変数である価格差と、張り付き（価格が買付価格に張り付いた案件）を作る。
#       ここで決めた J は、主な目的変数 R1（00c_買付期間末日.py）の起点にも用いる。
#       あわせて、以前の目的変数である20営業日の超過収益 post20 も計算する（02_回帰.py・03b_予測比較_条件.py の
#       post20 の設定と 04_注目度.py で用いる。論文の主な結果は R1 による）。
# 入力：株価（IR BANK の日次終値。data/prices/・data_old/prices/ に案件ごとに保存）、
#       TOPIX 連動ETF（1306）の日次終値（data/index_topix_etf.csv・data_old/index_topix_etf_all.csv）、
#       公表の時刻（TDnet の適時開示一覧 tob_announcements.csv）、案件一覧（tob_deals.csv）、標本（入力/標本413.csv）、
#       原文PDF（2022年以降は公開買付届出書、2019・2021年は開始の公表の適時開示）、入力/価格差_除外.csv、入力/買付価格修正.csv
# 出力：中間/収益と価格差.csv（01_分析表.py・00b・00c が読む）、中間/収益と価格差_照合.csv（以前の入力表との照合）
# 処理の流れ：①J を決める ②post20 を計算する ③原文から買付価格を読む ④換算係数 f を決める
#             ⑤プレミアム・価格差・張り付きを計算する ⑥以前の入力表と照合する
#
# 定義（日付は、個別株と指数の両方に終値がある取引日だけを数える。P＝個別株の終値、I＝1306 の終値）
#   J＝公表後最初の取引日：公表時刻が14時より前なら公表日以降の最初の取引日、14時以降または時刻不明なら公表日の翌日以降の最初の取引日。
#      J+1 は J の次の取引日、J−1 は J の前の取引日である。
#   AR_t＝日次の超過収益＝（P_t ÷ P_{t−1} − 1）−（I_t ÷ I_{t−1} − 1）
#   post20＝100 × Σ_{t＝J+2}^{J+21} AR_t（%。以前の処理と同じく、合計を小数第5位で丸めてから100倍する）。
#      01_分析表.py で 100×ln(1＋post20/100) に変換する
#   f＝株式分割・併合の換算係数。株価データは後の分割・併合にさかのぼって調整されているため、原文の買付価格（名目）を
#      株価データの単位に直すのに用いる。原文に書かれた「YYYY年M月D日 … 終値X円」のうち J−1 または公表日のもの
#      （なければ原文中のすべて）について、r＝株価データの終値 ÷ 原文の終値 を求め、1/r を分割比として自然な値
#      （整数、整数分の1、p/q：q≦6）に丸める（差が0.5%未満のものだけ）。最も多く現れた値を f とする。
#      原文に終値が1つもなければ f＝1 とする。原文から読めない3件は 入力/買付価格_確認メモ.csv の記録を使う
#   premium＝プレミアム＝（買付価格 ÷ f）÷ P_{J−1} − 1
#   spread_J1＝（買付価格 ÷ f）÷ P_{J+1} − 1。100倍したもの（01_分析表.py の sp）が論文の価格差である。
#      J の次の市場の取引日に個別株の売買がない案件と、入力/価格差_除外.csv の案件は計算しない
#   pinned＝張り付き＝1（|spread_J1|≦0.01、すなわち |価格差|≦1%）
import re, csv, unicodedata, os, numpy as np, pandas as pd, fitz
from collections import Counter
B = '../'; H = B + '再現/'
KEYS = pd.read_csv(H + '入力/標本413.csv').key

def closes(p):   # 日付→終値（終値が数値の行だけ）
    t = pd.read_csv(p, dtype=str); t['c'] = pd.to_numeric(t.close, errors='coerce'); t = t.dropna(subset=['c'])
    return dict(zip(t.date.str[:10], t.c))
def pub_times(p):   # （公表日, 表題の先頭30字）→ 公表時刻（公表日と表題で開示を特定する）
    return {(r['date'], r['title'][:30]): r.get('pub_time', '') for r in csv.DictReader(open(p, encoding='utf-8-sig'))}
SRC = {g: dict(idx=closes(B + f'{d}/{i}'), pub=pub_times(B + f'{d}/tob_announcements.csv'),
               deals=pd.read_csv(B + f'{d}/tob_deals.csv', dtype=str, keep_default_na=False), d=d)
       for g, d, i in [('new', 'data', 'index_topix_etf.csv'), ('old', 'data_old', 'index_topix_etf_all.csv')]}
OD = SRC['old']['deals'].assign(doc=lambda x: x.edinet_todokede.where(x.edinet_todokede != '', x.edinet_iken))   # 2019・2021年の適時開示ID（開始の公表がなければ意見表明）
OD = OD[OD.doc != ''].assign(key=lambda x: x.target_code + '_' + x.first_date).drop_duplicates('key').set_index('key').doc
MEMO = {'4492_2021-02-05': (None, 6.0), '7946_2021-03-08': (None, 5.0), '7597_2021-11-09': (2575.0, None)}   # 案件 → (買付価格, f)。入力/買付価格_確認メモ.csv の記録を書き写したもの（原文に終値がない、または文字が読み取れない3件）。None は原文から読んだ値を使う
EXCL = pd.read_csv(H + '入力/価格差_除外.csv', dtype=str).set_index('key').理由
# 分割比として自然な値：整数・整数分の1・p/q（q≦6）
CAND = np.array(sorted({p / q for p in range(1, 201) for q in range(1, 7)} | {1 / n for n in range(1, 201)}))
def snap(r):
    """比 r（株価データの終値 ÷ 原文の終値）から分割比 1/r に最も近い自然な値を返す。差が0.5%以上なら None。"""
    x = 1 / r; c = CAND[np.abs(CAND / x - 1).argmin()]; return float(c) if abs(c / x - 1) < 0.005 else None
def seireki(t):   # 平成・令和の年を西暦に直す
    t = re.sub(r'令和(元|\d+)年', lambda g: f'{2018 + (1 if g.group(1) == "元" else int(g.group(1)))}年', t)
    return re.sub(r'平成(\d+)年', lambda g: f'{1988 + int(g.group(1))}年', t)

rows = []
for k in KEYS:
    code, fd = k.split('_'); g = 'new' if fd >= '2022' else 'old'; s = SRC[g]
    P = closes(B + f'{s["d"]}/prices/{k}.csv'); I = s['idx']
    days = sorted(set(P) & set(I))
    # J（公表後最初の取引日）。時刻が取れない場合は hour＝99 とし、14時以降と同じ扱いにする
    d = s['deals']; d = d[(d.target_code == code) & (d.first_date == fd) & (d.status == '')]
    pt = s['pub'].get((fd, d.sample_title.iloc[0][:30]), '') if len(d) else ''
    hour = int(pt[11:13]) if len(pt) >= 13 else 99
    J = next(x for x in days if (x >= fd if hour < 14 else x > fd)); j = days.index(J)
    # post20（J+2〜J+21 の超過収益の和。株価データが J+21 までない案件は、データのある日までの和になる。日数は n_post20 に記録する）
    ar = [(P[days[i]] / P[days[i - 1]] - 1) - (I[days[i]] / I[days[i - 1]] - 1) for i in range(j + 2, min(j + 22, len(days)))]
    post20 = 100 * round(sum(ar), 5)
    # 原文の買付価格（05_買付価格の照合.py と同じ読み方）
    doc = d.edinet_todokede.iloc[0] if g == 'new' else OD.get(k, '')
    t = re.sub(r'\s+', '', unicodedata.normalize('NFKC', ''.join(p.get_text() for p in fitz.open(B + (f'data/edinet_pdf/{doc}.pdf' if g == 'new' else f'data_old/pdf/{doc}.pdf')))))
    m = None
    if g == 'new':   # 届出書：【買付け等の価格】の欄
        h = t.find('【買付け等の価格】'); seg = t[h:h + 600] if h >= 0 else ''
        m = re.search(r'()(普通株式)[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円', seg) or re.search(r'()()1株(につき|当たり)[、,]?金?([0-9,]+)円', seg)
    else:            # 適時開示：「買付け等の価格」の見出しの直後
        m = re.search(r'買付け等の価格[(（]?[0-9①]?[)）]?()(普通株式|株券)[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円', t)
        for hh in ([] if m else re.finditer(r'買付け等の価格', t)):
            m = re.match(r'.{0,80}?()(普通株式|株券)?[^円]{0,30}?1株(につき|当たり)[、,]?金?([0-9,]+)円', t[hh.end():hh.end() + 200])
            if m: break
    offer = float(m.group(4).replace(',', '')) if m else np.nan
    # 換算係数 f
    ev = []
    for mm in re.finditer(r'(\d{4})年(\d+)月(\d+)日[^。円]{0,80}?終値(は)?([0-9,.]+)円', seireki(t)):
        dt = f'{mm.group(1)}-{int(mm.group(2)):02d}-{int(mm.group(3)):02d}'; x = float(mm.group(5).replace(',', '') or 0)
        if dt in P and x > 0: ev.append((dt, P[dt] / x))
    near = [r for dt, r in ev if dt in (days[j - 1], fd)]
    cnt = Counter(f for f in map(snap, near or [r for _, r in ev]) if f)
    f, basis = (cnt.most_common(1)[0][0], ('公表日前後の終値' if near else '原文中の終値') + f'（{sum(cnt.values())}か所）') if cnt else (1.0, '原文に終値の記載なし')
    if k in MEMO:
        offer = MEMO[k][0] or offer; f = MEMO[k][1] or f; basis = '入力/買付価格_確認メモ.csv'
    off = offer / f
    sp = off / P[days[j + 1]] - 1
    nxt = min(x for x in I if x > J)   # J の次の市場の取引日。J+1 がこれと違えば、その日に個別株の売買がなかったことになる
    why = '' if days[j + 1] == nxt else 'J の翌営業日に売買がない'
    if k in EXCL: why = EXCL[k]
    if why: sp = np.nan
    rows.append({'key': k, 'jump_day': J, '公表時刻': pt, 'post20_raw': post20, 'n_post20': len(ar),
                 '買付価格_原文': offer, '調整係数': f, '調整係数の根拠': basis, '終値_J前日': P[days[j - 1]], '終値_J翌日': P[days[j + 1]],
                 'premium': off / P[days[j - 1]] - 1, 'spread_J1': sp, 'pinned': float(abs(sp) <= 0.01) if sp == sp else np.nan, '価格差なしの理由': why})
R = pd.DataFrame(rows).set_index('key')
R.to_csv(H + '中間/収益と価格差.csv', encoding='utf-8-sig')

# 以前の入力表（Codex の prepare.py・correct_and_rerun.py が作った prepared_data_corrected.csv／prepared_old.csv）と照合する。
# 値が違う案件は、違う理由（買付価格の修正など）とともに 中間/収益と価格差_照合.csv に書き出す
o = pd.concat([pd.read_csv(H + '入力/prepared_data_corrected.csv', dtype={'code': str}, keep_default_na=False),
               pd.read_csv(H + '入力/prepared_old.csv', dtype={'code': str}, keep_default_na=False)])
o = o.assign(key=o.code + '_' + o.event_date).drop_duplicates('key').set_index('key').loc[KEYS]
F = pd.read_csv(H + '入力/買付価格修正.csv', dtype=str).set_index('key')
NOTE = {'6574_2023-05-12': '以前の表は株価データの丸め（5.0円）のため買付価格（調整後5.0円）と同じ値になりプレミアム0としていた。原文の終値515円に対して買付価格500円で、正しくは−2.9%'}
cmp = []
for c in ['post20_raw', 'premium', 'spread_J1', 'pinned']:
    old = pd.to_numeric(o['post20_pp' if c == 'post20_raw' else c], errors='coerce'); new = R[c]
    same = ((new - old).abs() < 1e-4) | (new.isna() & old.isna())
    for k in R.index[~same]:
        cmp.append({'key': k, '項目': c, '以前の入力表': old[k], '再計算': new[k],
                    '理由': '買付価格の誤りを修正（入力/買付価格修正.csv）' if k in F.index else NOTE.get(k, '')})
cmp = pd.DataFrame(cmp, columns=['key', '項目', '以前の入力表', '再計算', '理由'])
cmp.to_csv(H + '中間/収益と価格差_照合.csv', index=False, encoding='utf-8-sig')
print('収益と価格差', len(R), '件｜J の一致', int((R.jump_day == o.jump_day.str[:10]).sum()), '｜価格差あり', int(R.spread_J1.notna().sum()))
print('以前の入力表と違う値', len(cmp), '個'); print(cmp.to_string())
