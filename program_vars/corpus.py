# 生成AIに読ませたものと同一の入力（キーワードで機械的に切り出し、名称を伏せた段落）を読み込む。戻り値は {案件: {段の名前: 本文}}
# 届出書 7 段：price/rival/board/shareholder/funding/regulatory/structure；意見表明 4 段：committee/policy/valuation/mom
import re, glob, os, pandas as pd
FS = '../fill_summary/'
DO = '../data_old/'
def secs(t):
    out = {}; parts = re.split(r'==== \[(\w+)\][^\n]*====', t)
    for i in range(1, len(parts), 2): out[parts[i]] = parts[i + 1].strip()
    return out
def load():
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
if __name__ == '__main__':
    C = load(); S = pd.read_csv('ai_vars_411.csv', index_col=0)
    miss = [k for k in S.index if k not in C]; print('案件', len(C), '主样本缺', len(miss), miss[:5])
    from collections import Counter; print(Counter(s for k in S.index if k in C for s in C[k]))
