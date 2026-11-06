# 原文の書類（公開買付届出書・意見表明報告書。2019・2021年は適時開示）をページ単位で読み込み、判定の根拠文がどの書類の何ページにあるかを引けるようにする
# 正規化は cut_sections.py の clean() と同じ（NFKC・空白除去・EDINET ヘッダ除去）
import os, re, pickle, unicodedata, fitz, pandas as pd
B = '../'
CACHE = B + 'program_vars/fulltext_pages.pkl'
def clean(t):
    t = unicodedata.normalize('NFKC', t)
    t = re.sub(r'EDINET提出書類\s*\S{0,60}?\(E\d{5}\)\s*(公開買付届出書|意見表明報告書)\s*(\d+/\d+)?', '', t)
    return re.sub(r'\s+', '', t)
def docs():
    out = {}
    for f, pdfdir in [('data/tob_deals.csv', 'data/edinet_pdf/'), ('data_old/tob_deals.csv', 'data_old/pdf/')]:
        T = pd.read_csv(B + f, dtype=str)
        for r in T.itertuples():
            k = f'{r.target_code}_{r.first_date}'
            out[k] = [(kind, d, B + pdfdir + f'{d}.pdf') for kind, d in [('届出書' if 'data/' == f[:5] else '開始の公表', r.edinet_todokede), ('意見表明', r.edinet_iken)] if isinstance(d, str) and d]
    return out
def load(keys):
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
    """根拠文のうち規則に該当した部分の文字列（位置の特定に用いる）。規則がなければ空"""
    if not pat or pat == '数値条件': return ''
    try: m = re.search(pat, sentence)
    except re.error: return ''
    return re.split(r'■■', m.group(0))[0][:14] if m else ''


def locate(P, k, sentence, anchor=''):
    """根拠文が原文のどのページにあるかを探し、(資料, 文書ID, ページ) を返す。
    根拠文を18字ずつの断片（伏せ字■■を除く）に分けて含むページを探す。anchor（規則に該当した文字列）があれば、それも含むページを優先し、
    「措置及び利益相反を回避…」のようにどこにでもある定型句でページを誤らないようにする"""
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
if __name__ == '__main__':
    S = pd.read_csv(B + 'program_vars/ai_vars_411.csv', index_col=0)
    P = load(S.index); print(len(P), sum(1 for k in S.index if P.get(k)), sum(len(P[k]) for k in S.index))
