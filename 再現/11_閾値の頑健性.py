# 11_閾値の頑健性.py：標本を分ける閾値を変えても主な結果が変わらないかを確かめる（頑健性の確認）
#
# 目的
#   論文の本文で標本を分けるのに使う次の2つの閾値を動かし、閾値の選び方に結果が左右されていないかを見る。
#     T：張り付きの閾値。|価格差|≦T% の全部買付けを「張り付いた全部買付け」とする（本文では事前に固定した T＝1%）。
#     G：部分買付けを価格差で分ける閾値。価格差 G% 超と G% 以下で平均収益を比べる（本文では G＝2%）。
#   価格差＝100×((買付価格/f)/J+1 の終値 − 1)。J は公表後最初の取引日、f は株式分割などの調整係数である。
#   目的変数は J+2〜J+21 の20営業日の TOPIX を引いた超過収益（post20_pp、対数、%）であり、主結果の R1 ではない。
#   回帰は 収益＝定数＋効果×条件の有無＋係数×価格差、標準誤差は HC1（不均一分散に頑健な標準誤差）である。
#
# 入力ファイル
#   中間/分析表_413.csv（01_分析表.py）
# 出力ファイル
#   なし（結果は画面に出す）
#
# 実行方法
#   python3 11_閾値の頑健性.py
import pandas as pd, numpy as np, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy import stats
A=pd.read_csv('../再現/中間/分析表_413.csv',index_col=0,dtype={'code':str})
S=A[A.post20_pp.notna()&A.sp.notna()].copy(); pb=S.PG_部分買付け==1
def reg(sub,v):
    """標本 sub で収益を条件 v と価格差に回帰し、「係数 (p 値, 該当件数/対象件数)」の文字列を返す。"""
    x=sm.add_constant(sub[[v,'sp']].astype(float)); r=sm.OLS(sub.post20_pp.astype(float),x).fit(cov_type='HC1')
    return f"{r.params[v]:+.2f} (p={r.pvalues[v]:.3f}, {int(sub[v].sum())}/{len(sub)})"
print('== 張り付きの閾値 T を変える（全部買付けを「自由に動く」と「張り付き」に分ける）')
for T in [0.5,1,2,3]:
    pin=S.sp.abs()<=T; F=S[~pb&~pin]; P=S[~pb&pin]
    print(f'T={T}%  自由に動く {len(F)}件 / 張り付き {len(P)}件')
    for v,l in [('PG_入札競合','入札・競合'),('PG_fund','ファンド'),('PG_親子上場','親子上場')]:
        print(f'   {l:6s} 自由に動く {reg(F,v)}   張り付き {reg(P,v)}')
print('\n== 部分買付けの閾値 G を変える（価格差 G% 超・G% 以下それぞれの平均収益を0と比べる t 検定）')
P=S[pb]
for G in [0,1,2,3,4,5]:
    hi=P[P.sp>G]; lo=P[P.sp<=G]
    print(f'G={G}%  超 {len(hi)}件 平均 {hi.post20_pp.mean():+.2f} p={stats.ttest_1samp(hi.post20_pp,0).pvalue:.3f} | 以下 {len(lo)}件 平均 {lo.post20_pp.mean():+.2f} p={stats.ttest_1samp(lo.post20_pp,0).pvalue:.3f}')
# 閾値を置かない場合：部分買付けの収益を価格差に直接回帰する
x=sm.add_constant(P[['sp']].astype(float)); r=sm.OLS(P.post20_pp,x).fit(cov_type='HC1')
print(f'\n閾値なし：部分買付け {len(P)}件で 収益＝a＋b×価格差 を推定  b={r.params.sp:+.3f} p={r.pvalues.sp:.3f}')
print(f'価格差と収益の順位相関（Spearman） {stats.spearmanr(P.sp,P.post20_pp)}')
