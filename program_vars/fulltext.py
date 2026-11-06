# 原文の書類をページ単位で読み込み、判定の根拠文がどの書類の何ページにあるかを特定する
#
# 目的：build_all.py が書き出す 判定の記録.csv の「資料・文書ID・ページ」列を作り、プログラム判定を原文で確かめられるようにする。
#       また、rules.py のうち買付者の種類（ファンド・MBO）の判定は、ここで読み込んだ全文を用いる。
# 入力：data/tob_deals.csv・data_old/tob_deals.csv（案件と書類IDの対応）
#       原文PDF：2022年以降は公開買付届出書と意見表明報告書（data/edinet_pdf/）、
#                2019・2021年は公開買付けの開始の公表と意見表明の適時開示（data_old/pdf/）
# 出力：program_vars/fulltext_pages.pkl（ページごとの正規化した本文。PDFの読み込みに時間がかかるため保存しておく）
# 処理の流れ：①案件ごとに書類のPDFを特定する ②ページごとに正規化して保存する ③根拠文の断片を含むページを探す
# 正規化は、段落の切り出しに用いた cut_sections.py（このリポジトリには含めていない）の clean() と同じである。
import os, re, pickle, unicodedata, fitz, pandas as pd
B = '../'
CACHE = B + 'program_vars/fulltext_pages.pkl'
def clean(t):
    """NFKC で全角・半角をそろえ、EDINET のページ見出しと空白をすべて除く。"""
    t = unicodedata.normalize('NFKC', t)
    t = re.sub(r'EDINET提出書類\s*\S{0,60}?\(E\d{5}\)\s*(公開買付届出書|意見表明報告書)\s*(\d+/\d+)?', '', t)
    return re.sub(r'\s+', '', t)
def docs():
    """案件 key → [(資料の種類, 文書ID, PDFのパス), …] を返す。

    資料の種類は、2022年以降が「届出書」「意見表明」、2019・2021年が「開始の公表」「意見表明」である。"""
    out = {}
    for f, pdfdir in [('data/tob_deals.csv', 'data/edinet_pdf/'), ('data_old/tob_deals.csv', 'data_old/pdf/')]:
        T = pd.read_csv(B + f, dtype=str)
        for r in T.itertuples():
            k = f'{r.target_code}_{r.first_date}'
            out[k] = [(kind, d, B + pdfdir + f'{d}.pdf') for kind, d in [('届出書' if 'data/' == f[:5] else '開始の公表', r.edinet_todokede), ('意見表明', r.edinet_iken)] if isinstance(d, str) and d]
    return out
def load(keys):
    """案件 key → [(資料の種類, 文書ID, [各ページの本文]), …] を返す。

    保存済みの案件はそのまま使い、まだ読んでいない案件だけ PDF を読んで保存に加える。"""
    P = pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else {}
    D = docs(); new = False
    for k in keys:
        if k in P: continue
        P[k] = []
        for kind, d, p in D.get(k, []):
            if os.path.exists(p): P[k].append((kind, d, [clean(pg.get_text()) for pg in fitz.open(p)]))
        new = True
    if new: pickle.dump(P, open(CACHE, 'wb'))
    return P
def anchor_of(sentence, pat):
    """根拠文のうち、規則（正規表現 pat）に該当した部分の先頭14字を返す。

    ページの特定に用いる。規則がない場合や数値条件で判定した場合は空文字を返す。
    根拠文では社名などが伏せ字「■■」になっているため、伏せ字の手前までを使う。"""
    if not pat or pat == '数値条件': return ''
    try: m = re.search(pat, sentence)
    except re.error: return ''
    return re.split(r'■■', m.group(0))[0][:14] if m else ''


def locate(P, k, sentence, anchor=''):
    """根拠文が原文のどのページにあるかを探し、(資料の種類, 文書ID, ページ番号) を返す。見つからなければ空文字3つを返す。

    根拠文を伏せ字「■■」・省略「…」・「：」で区切り、18字ずつの断片に分ける。先頭12個の断片を多く含むページほど有力とする。
    anchor（規則に該当した文字列）を含むページは、断片の数にかかわらず優先する。
    「措置及び利益相反を回避…」のような、どの書類にもある定型句だけで誤ったページを選ばないためである。"""
    frags = []
    for seg in re.split(r'■■|…|：', sentence):
        seg = seg.strip('。、()（）')
        for i in range(0, max(1, len(seg) - 18), 18):
            if len(seg[i:i + 18]) == 18: frags.append(seg[i:i + 18])
    cands = []
    for kind, d, pages in P.get(k, []):
        for i, pg in enumerate(pages):
            n = sum(f in pg for f in frags[:12])
            if n: cands.append((bool(anchor) and anchor in pg, n, kind, d, i + 1))
    if not cands: return ('', '', '')
    best = max(cands, key=lambda x: (x[0], x[1]))
    return best[2:]
if __name__ == '__main__':   # 確認用：保存した案件数、原文のある案件数、書類の総数を表示する
    S = pd.read_csv(B + 'program_vars/ai_vars_411.csv', index_col=0)
    P = load(S.index); print('保存した案件', len(P), '｜原文のある案件', sum(1 for k in S.index if P.get(k)), '｜書類の数', sum(len(P[k]) for k in S.index))
