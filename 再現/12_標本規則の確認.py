# 標本のうち「意見表明報告書が J+1 の15時より後に提出」の3件を除いても主な結果が変わらないかを見る
import pandas as pd, numpy as np, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy import stats
H='../再現/'
A=pd.read_csv(H+'中間/分析表_413.csv',index_col=0,dtype={'code':str})
S=A[A.post20_pp.notna()&A.sp.notna()]
D=['4477_2025-05-07','6736_2024-06-10','9362_2024-10-18']
def run(S,tag):
    pb=S.PG_部分买付==1; F=S[~pb&(S.pinned!=1)]
    def reg(sub,v,c=()):
        r=sm.OLS(sub.post20_pp,sm.add_constant(sub[[v,'sp',*c]].astype(float))).fit(cov_type='HC1'); return f'{r.params[v]:+.2f} (p={r.pvalues[v]:.3f})'
    hi=S[pb&(S.sp>2)].post20_pp
    print(f'{tag} {len(S)}件 | 入札 全体 {reg(S,"PG_入札競合",["PG_部分买付"])} 自由 {reg(F,"PG_入札競合")} | ファンド 全体 {reg(S,"PG_fund",["PG_部分买付"])} | 親子 全体 {reg(S,"PG_親子上場",["PG_部分买付"])} | 部分2%超 {hi.mean():+.2f} (p={stats.ttest_1samp(hi,0).pvalue:.3f}, {len(hi)}件)')
run(S,'現在')
run(S.drop([k for k in D if k in S.index]),'3件除外')
