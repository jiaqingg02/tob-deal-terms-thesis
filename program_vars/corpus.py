# 生成AIに読ませたものと同一の書類の段落を読み込む
#
# 目的：rules.py の判定の入力を作る。段落は、書類からキーワードで機械的に切り出し、社名などを伏せ字にしたものである。
#       生成AIと同じ入力を用いることで、プログラム判定と生成AIの判定を同じ条件で比べられる。
# 入力：fill_summary/{full,ext,pilot20}/…/*.txt … 2022年以降の公開買付届出書の段落（ファイル名が案件 key）
#       fill_summary/old/inputs/O*.txt         … 2019・2021年の開始の公表（適時開示）の段落
#       fill_summary/iken/inputs/K*.txt        … 2022年以降の意見表明報告書の段落
#       fill_summary/iken_old/inputs/Q*.txt    … 2019・2021年の意見表明（適時開示）の段落
#       O・K・Q のファイル名は、生成AIが会社を特定できないように付けた番号である。
#       番号から案件 key への対応は data_old/ai_id_map_DO_NOT_GIVE_TO_AI.csv（O・Q）と fill_summary/iken/id_map.csv（K）にある。
# 出力：ファイルは出力しない。load() が {案件 key: {段落の名前: 本文}} を返す。
#       届出書の7段落：price / rival / board / shareholder / funding / regulatory / structure
#       意見表明の4段落：committee / policy / valuation / mom（各段落の内容は rules.py の冒頭を参照）
import re, glob, os, pandas as pd
FS = '../fill_summary/'
DO = '../data_old/'
def secs(t):
    """「==== [段落の名前] … ====」の見出しで区切られたテキストを {段落の名前: 本文} にする。"""
    out = {}; parts = re.split(r'==== \[(\w+)\][^\n]*====', t)
    for i in range(1, len(parts), 2): out[parts[i]] = parts[i + 1].strip()
    return out
def load():
    """全案件の段落を読み込み、{案件 key: {段落の名前: 本文, '_key': 案件 key}} を返す。

    届出書（開始の公表）と意見表明の段落は、同じ案件 key の下にまとめる。"""
    C = {}
    for d in ['full/inputs', 'ext/inputs', 'pilot20/inputs_v2']:
        for f in glob.glob(FS + d + '/*.txt'): C.setdefault(os.path.basename(f)[:-4], {}).update(secs(open(f).read()))
    O = pd.read_csv(DO + 'ai_id_map_DO_NOT_GIVE_TO_AI.csv')
    om, qm = O.set_index('oid').key, O.set_index('qid').key
    for f in glob.glob(FS + 'old/inputs/O*.txt'): C.setdefault(om[os.path.basename(f)[:-4]], {}).update(secs(open(f).read()))
    km = pd.read_csv(FS + 'iken/id_map.csv').set_index('aid').key
    for f in glob.glob(FS + 'iken/inputs/K*.txt'): C.setdefault(km[os.path.basename(f)[:-4]], {}).update(secs(open(f).read()))
    for f in glob.glob(FS + 'iken_old/inputs/Q*.txt'): C.setdefault(qm[os.path.basename(f)[:-4]], {}).update(secs(open(f).read()))
    for k in C: C[k]['_key'] = k
    return C
if __name__ == '__main__':   # 確認用：段落のない案件の数と、段落ごとの案件数を表示する
    C = load(); S = pd.read_csv('ai_vars_411.csv', index_col=0)
    miss = [k for k in S.index if k not in C]; print('案件', len(C), '｜主標本で段落のない案件', len(miss), miss[:5])
    from collections import Counter; print(Counter(s for k in S.index if k in C for s in C[k]))
