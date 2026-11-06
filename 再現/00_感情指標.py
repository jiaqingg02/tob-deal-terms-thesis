# 従来の感情指標（辞書法）を原文から計算する
#
# 目的：予測比較（03_予測比較.py・03b_予測比較_条件.py）の「② 数値＋感情指標」で、書類の取引条件と比べる対照として用いる
#       3つの指標を作る。新聞見出しの語調・見出しの数・意見表明報告書の語調である。
#       辞書は xgb_compare/LEXICON.md（このリポジトリには含めていない）と同じで、結果を見る前に固定したものである。
# 入力：入力/prepared_data_corrected.csv（2022年以降の案件一覧）、入力/prepared_old.csv（2019・2021年の案件一覧）、
#       data_old/tob_deals.csv（2019・2021年の案件と意見表明の適時開示IDの対応）
#       新聞見出し：公表前30日の株探の見出し（data/news_windows/・data_old/news_windows/ に案件ごとに保存）
#       意見表明報告書：2022年以降は EDINET のPDF（data/edinet_pdf/）、2019・2021年は適時開示のテキスト（data_old/text/）
#       旧版の値：入力/traditional_sentiment_旧.csv・入力/traditional_sentiment_old.csv（照合用）
# 出力：中間/感情指標.csv（01_分析表.py が読む）。旧版の値との照合結果は画面に表示する
# 処理の流れ：①見出しの語調と数を数える ②意見表明報告書の「意見の内容、根拠及び理由」以降の本文の語調を数える
#             ③旧版の値と照合する
# 語調＝（肯定語の出現回数 − 否定語の出現回数）÷（両者の合計）。どちらも現れなければ 0 とする。
# 旧版は意見表明報告書のテキストを一時フォルダから読んでいたため、ここでは PDF から直接読み直し、値が再現できるかを確かめる。
import os, re, unicodedata, fitz, numpy as np, pandas as pd
B = '../'; H = B + '再現/'
# NP・NN＝新聞見出しの肯定語・否定語、DP・DN＝意見表明報告書の肯定語・否定語
NP = '上方修正 増益 最高益 増配 好調 上昇 高値 急騰 続伸 反発 黒字 受注 提携 ストップ高 増収 復配 好感 上振れ'.split()
NN = '下方修正 減益 赤字 減配 無配 不振 下落 安値 急落 続落 反落 損失 減収 ストップ安 懸念 不祥事 訴訟 下振れ 特損 債務超過'.split()
DP = '賛同 推奨 妥当 公正 相当 合理的 向上 シナジー 成長'.split()
DN = '反対 留保 不十分 困難 懸念 リスク 不利益 損失 毀損'.split()
def tone(t, P, N):
    """テキスト t の語調を返す。P・N は肯定語・否定語の一覧である。"""
    p = sum(t.count(w) for w in P); n = sum(t.count(w) for w in N)
    return (p - n) / (p + n) if p + n else 0.0
def news(path):
    """案件の見出しファイルから (見出しの語調, 見出しの数) を返す。ファイルがなければ (0, 0) とする。"""
    if not os.path.exists(path): return 0.0, 0
    x = pd.read_csv(path); return tone(unicodedata.normalize('NFKC', ' '.join(x.title.astype(str))), NP, NN), len(x)
rows = []
# 2022年以降の案件：意見表明報告書は EDINET のPDF
d = pd.read_csv(H + '入力/prepared_data_corrected.csv', dtype={'code': str}, keep_default_na=False)
for r in d.itertuples():
    k = f'{r.code}_{r.event_date}'; o = {'key': k}
    o['報道見出しの語気'], o['報道見出しの数'] = news(f'{B}data/news_windows/{k}.csv')
    g = f'{B}data/edinet_pdf/{r.edinet_iken}.pdf'; o['意見表明語気'] = np.nan
    if r.edinet_iken and os.path.exists(g):
        t = re.sub(r'\s+', '', unicodedata.normalize('NFKC', ''.join(p.get_text() for p in fitz.open(g))))
        i = [m.start() for m in re.finditer(r'【当該公開買付けに関する意見の内容、根拠及び理由】', t)]
        o['意見表明語気'] = tone(t[i[-1]:] if i else t, DP, DN)   # 見出しが複数回現れるときは最後のもの以降、見出しがなければ全文を使う
    rows.append(o)
# 2019・2021年の案件：意見表明の適時開示のテキスト（scripts_old/build_sentiment_old.py と同じ切り出し方）
o_ = pd.read_csv(H + '入力/prepared_old.csv', dtype={'code': str}, keep_default_na=False)
D = pd.read_csv(B + 'data_old/tob_deals.csv', dtype=str, keep_default_na=False); D['key'] = D.target_code + '_' + D.first_date; D = D[D.status == ''].set_index('key')
for r in o_.itertuples():
    k = f'{r.code}_{r.event_date}'; o = {'key': k}
    o['報道見出しの語気'], o['報道見出しの数'] = news(f'{B}data_old/news_windows/{k}.csv')
    di = D.loc[k, 'edinet_iken'] if k in D.index else ''; g = f'{B}data_old/text/{di}.txt'; o['意見表明語気'] = np.nan
    if di and os.path.exists(g):
        t = re.sub(r'\s+', '', unicodedata.normalize('NFKC', open(g, encoding='utf-8', errors='ignore').read()))
        m = re.search(r'[0-9]\.(?:本公開買付け|当該公開買付け)に関する意見の内容、根拠及び理由', t)
        o['意見表明語気'] = tone(t[m.start():] if m else t, DP, DN)
    rows.append(o)
S = pd.DataFrame(rows).drop_duplicates('key').set_index('key'); S.to_csv(H + '中間/感情指標.csv', encoding='utf-8-sig')
# 旧版の値との照合（列ごとに、一致した件数・最大の差・片方だけ欠測の件数）
old = pd.concat([pd.read_csv(H + '入力/traditional_sentiment_旧.csv'), pd.read_csv(H + '入力/traditional_sentiment_old.csv')]).drop_duplicates('key').set_index('key')
old = old.rename(columns={'新闻标题语气': '報道見出しの語気', '新闻标题数': '報道見出しの数'})   # 旧版のファイルの列名は作成時の名前のため読み替える
for c in ['報道見出しの語気', '報道見出しの数', '意見表明語気']:
    a, b = S[c].reindex(old.index), old[c]; ok = a.notna() & b.notna()
    print(f'{c}：照合 {int(ok.sum())} 件、一致 {int(np.isclose(a[ok], b[ok], atol=1e-9).sum())} 件、最大差 {float((a[ok] - b[ok]).abs().max()):.4f}、片方だけ欠測 {int((a.isna() != b.isna()).sum())} 件')
