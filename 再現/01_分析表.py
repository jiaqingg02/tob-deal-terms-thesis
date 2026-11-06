# 01_分析表.py：分析に使う変数を案件ごとに1つの表（分析表）にまとめる
#
# 目的
#   02〜05・11・12 のすべての分析が読む分析表 中間/分析表_413.csv を作る。
#   標本は書類を読んだ413件（2022年以降339件、2019・2021年74件）である。うち2件は価格差が計算できないため回帰には入らない。
#
# 入力ファイル
#   入力/標本413.csv                   標本の案件キー（key＝証券コード_公表日）
#   入力/prepared_data_corrected.csv   2022年以降の案件の数値変数（市場区分・時価総額・報道件数など）と、データの入手可否の判定（avail_post など）
#   入力/prepared_old.csv              2019・2021年の案件の同じ変数
#   入力/prepared_data.json            予測モデルに入れる数値変数の一覧（FE13・POST_EXTRA・CONTINUOUS）
#   入力/targets_by_tob_end.csv        買付期間中の超過収益（W1_以前の計算。02 の post20 版で参考として使う）
#   中間/収益と価格差.csv              00a_収益と価格差.py の出力（J・20営業日の超過収益・プレミアム・価格差・張り付き）
#   中間/感情指標.csv                  00_感情指標.py の出力（予測比較で比べる従来の感情指標）
#   ../program_vars/pg_vars_411.csv    取引条件11項目の判定結果（program_vars/build_all.py の出力。判定の規則は rules.py）
#
# 出力ファイル
#   中間/分析表_413.csv
#
# 処理の流れ
#   1. 2022年以降と2019・2021年の数値変数を結合し、標本413件に絞る。
#   2. 収益・価格差は 00a の計算値に差し替える（入力表に残っている古い列は捨てる）。
#   3. 20営業日の超過収益を対数に直し、価格差を%に直す。
#   4. 感情指標と取引条件11項目を結合する。取引条件はすべて rules.py のキーワード・数値規則による判定であり、生成AIの判定は使わない。
#
# 実行方法
#   python3 01_分析表.py   （再現/ フォルダで実行する。全部実行.sh からも呼ばれる）
#
# 主な列名
#   J          公表後最初の取引日（公表が14時より前なら公表日以降の最初の取引日、14時以降・時刻不明なら翌日以降の最初の取引日）
#   post20_pp  J+2〜J+21 の TOPIX を引いた超過収益の対数（100×ln(1＋post20_raw/100)、%）。以前の版の目的変数で、主結果の R1 は 00c が別に計算する
#   sp         価格差（%）＝100×((買付価格/f)/J+1 の終値 − 1)。f は株式分割などの調整係数
#   pinned     張り付き（|価格差|≦1%なら1）
#   PG_*       rules.py による取引条件の判定（0/1）
import json, sys, numpy as np, pandas as pd
B = '../'; H = B + '再現/'; PV = B + 'program_vars/'
d = pd.read_csv(H + '入力/prepared_data_corrected.csv', dtype={'code': str}, keep_default_na=False)
o = pd.read_csv(H + '入力/prepared_old.csv', dtype={'code': str}, keep_default_na=False)
for x in (d, o): x['key'] = x.code + '_' + x.event_date
o = o[o.event_date.str[:4].isin(['2019', '2021'])]
A = pd.concat([d, o[~o.key.isin(d.key)]]).set_index('key')
# 標本：書類を読んだ413件。2022年以降は公開買付届出書と意見表明報告書が公表から2営業日目の15時までに提出された案件、
# 2019・2021年は公開買付けの開始の適時開示を読んだ案件である
KEYS = pd.read_csv(H + '入力/標本413.csv').key
A = A.loc[KEYS]
# 入力表に残っている次の列は使わない：収益・価格差の古い計算値（00a の値に差し替える）、
# 以前の版で生成AIが判定した列（h__・hybrid_・media_score など）、買付者類型の古いラベル（buy_fund・buy_mbo）
R = pd.read_csv(H + '中間/収益と価格差.csv', index_col=0)
drop = ['jump_day', 'post20_pp', 'n_post20', 'premium', 'spread_J1', 'pinned', 'spread_reason', 'buy_fund', 'buy_mbo', 'car_ann_pp', 'n_ann', 'media_score', 'media_status']
A = A.drop(columns=[c for c in A.columns if c in drop or c.startswith(('h__', 'hybrid_', 'in_hybrid', 'in_media'))])
A = A.join(R[['jump_day', 'post20_raw', 'n_post20', 'premium', 'spread_J1', 'pinned']])
meta = json.load(open(H + '入力/prepared_data.json'))
NUM = [c for c in meta['FE13'] + meta['POST_EXTRA'] if c not in ('buy_fund', 'buy_mbo')]
for c in NUM: A[c] = pd.to_numeric(A[c], errors='coerce')
A['post20_pp'] = 100 * np.log1p(A.post20_raw / 100)   # J+2〜J+21 の超過収益の対数（%）
A['sp'] = 100 * A.spread_J1                           # 価格差（%）
A['date'] = A.event_date; A['年'] = A.event_date.str[:4].astype(int)
A = A.join(pd.read_csv(H + '入力/targets_by_tob_end.csv', dtype={'code': str}).rename(columns={'W1_期间内': 'W1_以前の計算'}).assign(key=lambda t: t.code + '_' + t.event_date).set_index('key')[['W1_以前の計算']])
A = A.join(pd.read_csv(H + '中間/感情指標.csv', index_col=0))
P = pd.read_csv(PV + 'pg_vars_411.csv', index_col=0)
# 価格差のない2件は pg_vars_411.csv に含まれないため、同じ規則（rules.py）でここで判定する。
# この2件は予測比較の訓練データにだけ入る（回帰には入らない）
sys.path.insert(0, PV); import corpus, fulltext, build_all
rest = [k for k in A.index if k not in P.index]
if rest:
    C = corpus.load(); FT = fulltext.load(rest)
    for k in rest:
        C[k]['_full'] = FT.get(k, [])
        for name, f, _, _ in build_all.VARS: P.loc[k, name] = f(C[k])[0]
A = A.join(P)
A.to_csv(H + '中間/分析表_413.csv', encoding='utf-8-sig')
print('分析表（行数, 列数）', A.shape, '／収益と価格差がそろい回帰に使える件数', int((A.post20_pp.notna() & A.sp.notna()).sum()))
