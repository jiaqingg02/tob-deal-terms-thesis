# 分析に使う表を1つにまとめる（413件＝2022年以降339件＋2019・2021年74件。うち価格差のない2件は回帰から除くので回帰は411件）
#   収益・プレミアム・価格差・張り付き：中間/収益と価格差.csv（00a_収益と価格差.py が株価と原文から計算）
#   その他の数値変数（市場・時価総額・市場区分・報道件数など）と入手可能性の判定：入力/prepared_data_corrected.csv（2022年以降）・入力/prepared_old.csv（2019・2021年）
#   買付期間中の収益：入力/targets_by_tob_end.csv
#   感情指標：中間/感情指標.csv（00_感情指標.py）
#   書類の条件：program_vars のプログラム判定（rules.py）。生成AIの判定は使わない（以前の版との照合は 01b_旧版の再現用.py）
import json, sys, numpy as np, pandas as pd
B = '../'; H = B + '再現/'; PV = B + 'program_vars/'
d = pd.read_csv(H + '入力/prepared_data_corrected.csv', dtype={'code': str}, keep_default_na=False)
o = pd.read_csv(H + '入力/prepared_old.csv', dtype={'code': str}, keep_default_na=False)
for x in (d, o): x['key'] = x.code + '_' + x.event_date
o = o[o.event_date.str[:4].isin(['2019', '2021'])]
A = pd.concat([d, o[~o.key.isin(d.key)]]).set_index('key')
# 標本：書類を読んだ413件（2022年以降は届出書・意見表明報告書が公表2営業日目15時までに提出された案件、2019・2021年は適時開示）
KEYS = pd.read_csv(H + '入力/標本413.csv').key
A = A.loc[KEYS]
# 収益・価格差の列と、以前の版の生成AIの列（h__・hybrid_・media_score）・買付者類型の旧ラベル（buy_fund・buy_mbo）はここでは使わない
R = pd.read_csv(H + '中間/収益と価格差.csv', index_col=0)
drop = ['jump_day', 'post20_pp', 'n_post20', 'premium', 'spread_J1', 'pinned', 'spread_reason', 'buy_fund', 'buy_mbo', 'car_ann_pp', 'n_ann', 'media_score', 'media_status']
A = A.drop(columns=[c for c in A.columns if c in drop or c.startswith(('h__', 'hybrid_', 'in_hybrid', 'in_media'))])
A = A.join(R[['jump_day', 'post20_raw', 'n_post20', 'premium', 'spread_J1', 'pinned']])
meta = json.load(open(H + '入力/prepared_data.json'))
NUM = [c for c in meta['FE13'] + meta['POST_EXTRA'] if c not in ('buy_fund', 'buy_mbo')]
for c in NUM: A[c] = pd.to_numeric(A[c], errors='coerce')
A['post20_pp'] = 100 * np.log1p(A.post20_raw / 100)   # 目的変数：20営業日の超過収益（対数、%）
A['sp'] = 100 * A.spread_J1                           # 価格差（%）
A['date'] = A.event_date; A['年'] = A.event_date.str[:4].astype(int)
A = A.join(pd.read_csv(H + '入力/targets_by_tob_end.csv', dtype={'code': str}).assign(key=lambda t: t.code + '_' + t.event_date).set_index('key')[['W1_期间内']])
A = A.join(pd.read_csv(H + '中間/感情指標.csv', index_col=0))
P = pd.read_csv(PV + 'pg_vars_411.csv', index_col=0)
# 価格差のない2件は pg_vars_411 にないので、同じ規則（rules.py）でここで判定する（予測比較の訓練にだけ入る）
sys.path.insert(0, PV); import corpus, fulltext, build_all
rest = [k for k in A.index if k not in P.index]
if rest:
    C = corpus.load(); FT = fulltext.load(rest)
    for k in rest:
        C[k]['_full'] = FT.get(k, [])
        for name, f, _, _ in build_all.VARS: P.loc[k, name] = f(C[k])[0]
A = A.join(P)
A.to_csv(H + '中間/分析表_413.csv', encoding='utf-8-sig')
print('分析表', A.shape, '回帰に使える件数（収益と価格差がある）', int((A.post20_pp.notna() & A.sp.notna()).sum()))
