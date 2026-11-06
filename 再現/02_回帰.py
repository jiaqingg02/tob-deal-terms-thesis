# 論文の主な結果（p.25〜32）を、プログラム判定の変数だけで計算する。生成AIの判定は使わない
#   使い方：python3 02_回帰.py（20営業日、従来）／python3 02_回帰.py W1（当初の買付期間の末日まで、TOPIX を引いた超過収益）
#         python3 02_回帰.py R1（論文の主結果：当初の買付期間の末日まで、株価そのものの保有収益・市場を引かない＋年ダミー。Hsieh and Walkling 2005 と同じ扱い）
#   回帰：その後20営業日の超過収益（対数、%）＝定数＋効果×条件の有無＋係数×価格差（＋全体では部分買付けの有無）。標準誤差は HC1、有意水準は10%
#   ① 部分買付けで価格差2%超：平均と t 検定（0との差）、2%以下との比較
#   ② 届出書の条件（価格が自由に動いた全部買付け／全体） ③ 意見表明報告書の条件 ④ 価格が買付価格に張り付いた案件（反面の証拠） ⑤ 2023年8月の経産省指針の後
import numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy import stats
import os; H = os.environ.get('SAIGEN', '../再現') + '/'   # Colab では環境変数 SAIGEN で置き場を指定
A = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str})
import sys; TGT = sys.argv[1] if len(sys.argv) > 1 else 'post20'   # post20＝J+2〜J+21（従来）／W1＝J+2〜届出書の当初の買付期間の末日（00c_買付期間末日.py）
if TGT == 'W1':
    W = pd.read_csv(H + '中間/買付期間末日.csv', index_col=0, keep_default_na=False)
    A['y'] = 100 * np.log1p(pd.to_numeric(W.W1_raw.reindex(A.index), errors='coerce') / 100)
elif TGT == 'R1':
    W = pd.read_csv(H + '中間/買付期間末日.csv', index_col=0, keep_default_na=False)
    A['y'] = 100 * np.log1p(pd.to_numeric(W.R1_raw.reindex(A.index), errors='coerce') / 100)
else: A['y'] = A.post20_pp
YD = TGT == 'R1'   # R1 では年ダミーで時期（市場全体の動き）を統制する
S = A[A.y.notna() & A.sp.notna()].copy()        # post20：411件
ITEMS = [('PG_入札競合', '入札・競合あり'), ('PG_没提价', '交渉で値上げされていない'), ('PG_fund', '買付者がファンド'), ('PG_mbo', 'MBO'),
         ('PG_大株主契約なし', '大株主の応募契約なし'), ('PG_取締役会中立', '取締役会が中立'), ('PG_許認可待ち', '許認可の承認待ち'), ('PG_自己資金', '自己資金')]
IKV = [('PG_優待廃止', '株主優待の廃止'), ('PG_親子上場', '親子上場の解消')]
def reg(sub, v, ctrl=()):
    sub = sub[sub[v].notna()]; x = sub[[v, 'sp'] + list(ctrl)].astype(float); k = int((x[v] != 0).sum())
    if YD: x = x.join(pd.get_dummies(sub.date.astype(str).str[:4], prefix='年', drop_first=True).astype(float))   # 標本の中で最も早い年を基準
    if k < 2 or len(sub) - k < 2: return dict(係数=np.nan, p=np.nan, 該当件数=k, 対象件数=len(sub))
    r = sm.OLS(sub.y.astype(float), sm.add_constant(x)).fit(cov_type='HC1')
    return dict(係数=round(r.params[v], 4), p=round(r.pvalues[v], 4), 該当件数=k, 対象件数=len(sub))
rows = []
def put(sec, lab, r): rows.append({'節': sec, '項目': lab, **r, '有意': '**' if r['p'] < .05 else '*' if r['p'] < .1 else ''})
def story(S, tag):
    pb, pin = S.PG_部分买付 == 1, S.pinned == 1; F, FP = S[~pb & ~pin], S[~pb & pin]
    hi, lo = S[pb & (S.sp > 2)], S[pb & (S.sp <= 2)]
    put(f'{tag}① 部分買付け', '価格差2%超の平均（0と比較）', dict(係数=round(hi.y.mean(), 4), p=round(stats.ttest_1samp(hi.y, 0).pvalue, 4), 該当件数=len(hi), 対象件数=int(pb.sum())))
    put(f'{tag}① 部分買付け', '価格差2%以下の平均（0と比較）', dict(係数=round(lo.y.mean(), 4), p=round(stats.ttest_1samp(lo.y, 0).pvalue, 4), 該当件数=len(lo), 対象件数=int(pb.sum())))
    w = hi['W1_期间内'].dropna()
    if TGT == 'post20': put(f'{tag}① 部分買付け', '価格差2%超・買付期間中の平均', dict(係数=round(w.mean(), 4), p=round(stats.ttest_1samp(w, 0).pvalue, 4), 該当件数=len(w), 対象件数=int(pb.sum())))
    for v, lab in ITEMS: put(f'{tag}② 価格が自由に動いた全部買付け', lab, reg(F, v))
    for v, lab in ITEMS[:4]: put(f'{tag}② 全体', lab, reg(S, v, ['PG_部分买付']))
    for v, lab in IKV:
        put(f'{tag}③ 全体', lab, reg(S, v, ['PG_部分买付'])); put(f'{tag}③ 全部買付け', lab, reg(S[~pb], v)); put(f'{tag}③ 価格が自由に動いた全部買付け', lab, reg(F, v))
    for v, lab in ITEMS[:4]: put(f'{tag}④ 張り付いた全部買付け', lab, reg(FP, v))
story(S, '')
story(S[S.date >= '2023-08-31'], '⑤指針後 ')
R = pd.DataFrame(rows); R.to_csv(H + ('結果/回帰.csv' if TGT == 'post20' else f'結果/回帰_{TGT}.csv'), index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200); print(f'標本 {len(S)} 件'); print(R.to_string(index=False))
