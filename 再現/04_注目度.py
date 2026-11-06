# 注目度の結果（p.33〜36）のうち、書類の条件を使う部分をプログラム判定の変数で計算し直す
#   注目度の指標そのもの（日経の報道・事前報道・株探の記事数・売買代金・合成注目度）は 00b_注目度の指標.py が計算した 中間/注目度の指標.csv
#   日々の累積収益の図（注目度①の22営業日目の値）は書類の条件を使わないので attention/fig_path.py のまま
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf, warnings; warnings.filterwarnings('ignore')
from scipy import stats
import os; B = '../'; H = os.environ.get('SAIGEN', B + '再現') + '/'
if 'SAIGEN' in os.environ: B = H   # Colab：株価も同じ置き場
A = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str})
T = pd.read_csv(H + '中間/注目度の指標.csv', index_col=0)[['日经_事后', '抢先报道_任一', '关注度', 'log売買代金']]
S = A[A.post20_pp.notna() & A.sp.notna()].join(T, rsuffix='_t'); S['nk'] = S.日经_事后 > 0
rows = []
def put(sec, lab, **k): rows.append({'節': sec, '項目': lab, **k}); print(sec, lab, k)
# 注目度①：価格差で説明できない部分の大きさ（日経の報道の有無）と、主な条件の効果（報道の有無別）
X = sm.add_constant(S[['sp', 'PG_部分买付']].astype(float)); S['ares'] = (S.post20_pp - sm.OLS(S.post20_pp, X).fit().predict(X)).abs()
put('注目度①', '説明できない部分の絶対値の平均（報道なし／あり）', 報道なし=round(S[~S.nk].ares.mean(), 2), 報道あり=round(S[S.nk].ares.mean(), 2), p=round(stats.mannwhitneyu(S[S.nk].ares, S[~S.nk].ares).pvalue, 4), 件数=f'{int((~S.nk).sum())}/{int(S.nk.sum())}')
def eff(sub, v):
    x = sub[[v, 'sp', 'PG_部分买付']].astype(float); r = sm.OLS(sub.post20_pp, sm.add_constant(x)).fit(cov_type='HC1'); return round(r.params[v], 2), round(r.pvalues[v], 3), int(x[v].sum())
for v, lab in [('PG_入札競合', '入札・競合あり'), ('PG_親子上場', '親子上場の解消'), ('PG_優待廃止', '株主優待の廃止')]:
    put('注目度①', f'{lab}の効果（報道なし／あり）', 報道なし=eff(S[~S.nk], v), 報道あり=eff(S[S.nk], v))
# 注目度②：部分買付けで価格差2%超の案件を注目度の高低で分ける
hi = S[(S.PG_部分买付 == 1) & (S.sp > 2)]; lo = hi.关注度 <= S.关注度.median()
put('注目度②', '部分買付け・価格差2%超の20営業日収益（注目度 低／高）', 低=round(hi[lo].post20_pp.mean(), 2), 高=round(hi[~lo].post20_pp.mean(), 2), p=round(stats.ttest_ind(hi[lo].post20_pp, hi[~lo].post20_pp, equal_var=False).pvalue, 3), 件数=f'{int(lo.sum())}/{int((~lo).sum())}', 順位相関=round(stats.spearmanr(hi.关注度, hi.post20_pp)[0], 2))
# 注目度③：前日基準プレミアムの中央値回帰（売買代金の対数の係数）。統制変数を変えたときの頑健性も出す
S['p'] = S.premium * 100; S['post'] = S.date >= '2023-08-31'
for ctrl, nm in [('log_mktcap', '時価総額'), ('log_mktcap + PG_fund + PG_mbo', '時価総額・ファンド・MBO'), ('log_mktcap + PG_fund + PG_mbo + PG_部分买付', '時価総額・ファンド・MBO・部分買付け')]:
    for sub, g in [(S, '全体'), (S[S.post], '指針後')]:
        r = smf.quantreg('p ~ log売買代金 + ' + ctrl, sub.dropna(subset=['p', 'log売買代金', 'log_mktcap'])).fit(q=.5)
        put('注目度③', f'売買代金（対数）の係数｜統制：{nm}｜{g}', 係数=round(r.params['log売買代金'], 2), p=round(r.pvalues['log売買代金'], 3), 件数=int(r.nobs))
pd.DataFrame(rows).to_csv(H + '結果/注目度.csv', index=False, encoding='utf-8-sig')
# 注目度③（続き）：公表日終値基準と60営業日前基準のプレミアム（中央値）。買付価格＝公表日の終値×(1＋プレミアム)（原文の買付価格と一致することを 05 で確認）
#   以前の版（attention/check2.py・fig_cde.py）は、公表日の前営業日の終値から買付価格を逆算しており、1日ずれていた。ここで正しく計算し直す
import glob
def p60(k):
    f = (glob.glob(B + f'data/prices/{k}.csv') + glob.glob(B + f'data_old/prices/{k}.csv'))
    if not f: return np.nan
    p = pd.read_csv(f[0]); ix = p.index[p.date <= k.split('_')[1]]
    if len(ix) <= 60: return np.nan
    c0, c60 = p.close.iloc[ix[-1]], p.close.iloc[ix[-1] - 60]
    return c0 * (1 + S.loc[k, 'premium']) / c60 - 1
S['p60'] = [100 * p60(k) for k in S.index]
med = S.log売買代金.median(); S['grp'] = np.where(S.抢先报道_任一 == 1, '事前報道あり', np.where(S.log売買代金 > med, '平常の売買代金 大', '平常の売買代金 小'))
for g, d in S.groupby('grp'):
    put('注目度③', f'プレミアムの中央値（{g}）', 公表日終値基準=round(d.p.median(), 1), 六十営業日前基準=round(d.p60.median(), 1), 件数=len(d))
nb = S[S.抢先报道_任一 == 0]; hi_, lo_ = nb[nb.log売買代金 > med], nb[nb.log売買代金 <= med]
put('注目度③', '売買代金 大／小（事前報道なし）の差の検定', 公表日終値基準p=round(stats.mannwhitneyu(hi_.p, lo_.p).pvalue, 3), 六十営業日前基準p=round(stats.mannwhitneyu(hi_.p60.dropna(), lo_.p60.dropna()).pvalue, 3))
pd.DataFrame(rows).to_csv(H + '結果/注目度.csv', index=False, encoding='utf-8-sig')
