# 12_標本規則の確認.py：標本の選び方の境界にある3件を除いても主な結果が変わらないかを確かめる（頑健性の確認）
#
# 目的
#   標本には、意見表明報告書が J+1（公表後最初の取引日 J の次の取引日）の15時より後に提出された案件が3件入っている。
#   J+1 の終値の時点で投資家が意見表明報告書の内容を知り得たかが、この3件では確かでない。
#   この3件を除いた場合と除かない場合で、主な結果（入札・競合あり、買付者がファンド、親子上場の解消の係数と、価格差2%超の部分買付けの平均収益）を比べる。
#   目的変数は J+2〜J+21 の20営業日の TOPIX を引いた超過収益（post20_pp、対数、%）であり、主結果の R1 ではない。
#   回帰は 収益＝定数＋効果×条件の有無＋係数×価格差（＋全体では部分買付けの有無）、標準誤差は HC1（不均一分散に頑健な標準誤差）である。
#
# 入力ファイル
#   中間/分析表_413.csv（01_分析表.py）
# 出力ファイル
#   なし（結果は画面に出す）
#
# 実行方法
#   python3 12_標本規則の確認.py   （全部実行.sh には含めていないので、個別に実行する）
import pandas as pd, numpy as np, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy import stats
H='../再現/'
A=pd.read_csv(H+'中間/分析表_413.csv',index_col=0,dtype={'code':str})
S=A[A.post20_pp.notna()&A.sp.notna()]
D=['4477_2025-05-07','6736_2024-06-10','9362_2024-10-18']   # 意見表明報告書が J+1 の15時より後に提出された3件（証券コード_公表日）
def run(S,tag):
    """標本 S で主な結果を計算し、tag を頭に付けて1行で画面に出す。"""
    pb=S.PG_部分買付け==1; F=S[~pb&(S.pinned!=1)]   # F＝自由に動く全部買付け（部分買付けでも張り付きでもない）
    def reg(sub,v,c=()):
        r=sm.OLS(sub.post20_pp,sm.add_constant(sub[[v,'sp',*c]].astype(float))).fit(cov_type='HC1'); return f'{r.params[v]:+.2f} (p={r.pvalues[v]:.3f})'
    hi=S[pb&(S.sp>2)].post20_pp
    print(f'{tag} {len(S)}件 | 入札・競合 全体 {reg(S,"PG_入札競合",["PG_部分買付け"])} 自由に動く全部買付け {reg(F,"PG_入札競合")} | ファンド 全体 {reg(S,"PG_fund",["PG_部分買付け"])} | 親子上場 全体 {reg(S,"PG_親子上場",["PG_部分買付け"])} | 部分買付け・価格差2%超の平均 {hi.mean():+.2f} (p={stats.ttest_1samp(hi,0).pvalue:.3f}, {len(hi)}件)')
run(S,'現在')
run(S.drop([k for k in D if k in S.index]),'3件除外')
