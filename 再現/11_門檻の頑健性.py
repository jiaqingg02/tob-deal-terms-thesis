# 門檻の頑健性：張り付き（|価格差|≦T）と部分買付けの価格差の分け目（G%）を変えて、主な結果が変わるかを見る
import pandas as pd, numpy as np, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy import stats
A=pd.read_csv('../再現/中間/分析表_413.csv',index_col=0,dtype={'code':str})
S=A[A.post20_pp.notna()&A.sp.notna()].copy(); pb=S.PG_部分买付==1
def reg(sub,v):
    x=sm.add_constant(sub[[v,'sp']].astype(float)); r=sm.OLS(sub.post20_pp.astype(float),x).fit(cov_type='HC1')
    return f"{r.params[v]:+.2f} (p={r.pvalues[v]:.3f}, {int(sub[v].sum())}/{len(sub)})"
print('== 張り付きの門檻 T を変える（全部買付けを 自由／張り付き に分ける）')
for T in [0.5,1,2,3]:
    pin=S.sp.abs()<=T; F=S[~pb&~pin]; P=S[~pb&pin]
    print(f'T={T}%  自由 {len(F)}件 / 張り付き {len(P)}件')
    for v,l in [('PG_入札競合','入札・競合'),('PG_fund','ファンド'),('PG_親子上場','親子上場')]:
        print(f'   {l:6s} 自由 {reg(F,v)}   張り付き {reg(P,v)}')
print('\n== 部分買付けの分け目 G を変える（価格差 G% 超の平均、0 と比較）')
P=S[pb]
for G in [0,1,2,3,4,5]:
    hi=P[P.sp>G]; lo=P[P.sp<=G]
    print(f'G={G}%  超 {len(hi)}件 平均 {hi.post20_pp.mean():+.2f} p={stats.ttest_1samp(hi.post20_pp,0).pvalue:.3f} | 以下 {len(lo)}件 平均 {lo.post20_pp.mean():+.2f} p={stats.ttest_1samp(lo.post20_pp,0).pvalue:.3f}')
x=sm.add_constant(P[['sp']].astype(float)); r=sm.OLS(P.post20_pp,x).fit(cov_type='HC1')
print(f'\n分け目なし：部分買付け69件で 収益＝a＋b×価格差  b={r.params.sp:+.3f} p={r.pvalues.sp:.3f}')
print(f'順位相関（価格差と収益） {stats.spearmanr(P.sp,P.post20_pp)}')
