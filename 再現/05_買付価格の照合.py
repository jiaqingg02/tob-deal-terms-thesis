# 05_買付価格の照合.py：価格差の計算に使った買付価格が、原文に書かれた買付価格と一致するかを1件ずつ確かめる
#
# 目的
#   価格差（＝100×((買付価格/f)/J+1 の終値 − 1)、f は株式分割などの調整係数）の元になる買付価格が正しいことを確認する。
#   論文の「価格差の計算」の説明にある照合の件数（原文から読めた件数・一致した件数・個別に確認した件数）を出す。
#
# 入力ファイル
#   中間/分析表_413.csv（01_分析表.py。価格差のある案件だけを照合する）
#   ../data_old/tob_deals.csv（2019・2021年の案件と、読む適時開示の書類ID）
#   ../data/prices・../data_old/prices（日次の株価）、../data/edinet_pdf・../data_old/pdf（原文のPDF）
#   入力/買付価格_確認メモ.csv（原文に終値の記載がない、または文字が取り出せない3件を個別に確認した記録）
# 出力ファイル
#   結果/買付価格の照合.csv（全件）。一致しなかった案件は画面にも出す
#
# 処理の流れ
#   1. 分析に使った買付価格を J+1 の終値×(1＋価格差) で逆算する。
#   2. 原文から買付価格を読む。2022年以降は公開買付届出書の【買付け等の価格】の欄、2019・2021年は適時開示の「買付け等の価格」の見出しの直後を読む。
#   3. 両者の比が1%以内なら一致とする。株価データは後の株式分割・併合でさかのぼって調整されていることがあるため、
#      原文に書かれた終値と株価データの終値の比（調整係数）で割っても2%以内なら「調整後に一致」とする。
#   4. それでも確認できない案件は 入力/買付価格_確認メモ.csv の記録で確認済みとする。
#   株式分割などで価格の単位を直した12件の記録は 以前の作業フォルダの修正記録に残してある（このリポジトリには含めていない）。
#
# 実行方法
#   python3 05_買付価格の照合.py
import re, unicodedata, fitz, numpy as np, pandas as pd, os
B = '../'; H = B + '再現/'
A = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str})
A = A[A.sp.notna()]
OD = pd.read_csv(B + 'data_old/tob_deals.csv', dtype=str, keep_default_na=False); OD['doc'] = OD.edinet_todokede.where(OD.edinet_todokede != '', OD.edinet_iken)   # 2019・2021年の適時開示の書類ID（開始の公表がなければ意見表明の開示）
OD = OD[OD.doc != ''].assign(key=lambda x: x.target_code + '_' + x.first_date).drop_duplicates('key').set_index('key').doc
A['doc'] = [r.edinet_todokede if r.年 >= 2022 else OD.get(k, '') for k, r in A.iterrows()]
rows = []
for k, r in A.iterrows():
    new = r.年 >= 2022; px = pd.read_csv(B + (f'data/prices/{k}.csv' if new else f'data_old/prices/{k}.csv')).set_index('date').close.astype(float)
    i = list(px.index).index(r.jump_day[:10]) if r.jump_day[:10] in px.index else None
    close2 = px.iloc[i + 1] if i is not None and i + 1 < len(px) else np.nan   # J+1 の終値
    used = close2 * (1 + r.spread_J1)
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
    rows.append({'案件': k, '原文の買付価格': doc, '分析に使った買付価格': round(used, 1), '比': round(used / doc, 4) if doc else np.nan, '株価データの調整係数': round(adj, 4), '原文': seg[:120]})
R = pd.DataFrame(rows); R['一致'] = (R.比 - 1).abs() < 0.01
R['調整後に一致'] = R.一致 | ((R.比 / R.株価データの調整係数 - 1).abs() < 0.02)
M = pd.read_csv(H + '入力/買付価格_確認メモ.csv').set_index('案件')   # 原文に終値の記載がない、または文字が取り出せない3件を個別に確認した記録（理由つき）
R['個別確認'] = R.案件.map(M.確認).fillna(''); R['確認済み'] = R.調整後に一致 | (R.個別確認 != '')
print('照合', len(R), '件｜原文から読めた', int(R.原文の買付価格.notna().sum()), '｜1%以内で一致', int(R.一致.sum()), '｜株式分割などの調整を考えると一致', int(R.調整後に一致.sum()), '｜個別確認を含め確認済み', int(R.確認済み.sum()))
R.to_csv(H + '結果/買付価格の照合.csv', index=False, encoding='utf-8-sig')
print(R[~R.一致].drop(columns='原文').to_string())
