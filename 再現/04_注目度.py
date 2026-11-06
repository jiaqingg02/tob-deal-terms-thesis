# 04_注目度.py：市場の注目度による結果の違いを、プログラムで判定した取引条件を使って計算する（論文の注目度の節）
#
# 目的
#   注目度の節の数値のうち、取引条件を使うものを計算する。
#     注目度①  回帰で説明できない収益の大きさを日経の報道の有無で比べ、主な条件の効果も報道の有無別に推定する
#     注目度②  価格差2%超の部分買付けを、合成注目度の高低（中央値で分ける）で比べる
#     注目度③  プレミアム（買付価格の上乗せ率）と平常時の売買代金の関係（中央値回帰）と、基準日の違うプレミアムの中央値
#   目的変数は J+2〜J+21 の20営業日の TOPIX を引いた超過収益（post20_pp、対数、%）である。
#   主結果の R1（当初の買付期間の末日までの保有収益）ではない点に注意する。
#   日々の累積収益の図は取引条件を使わないため、このファイルでは作らない（以前の版の attention/fig_path.py。このリポジトリには含めていない）。
#
# 入力ファイル
#   中間/分析表_413.csv（01_分析表.py）
#   中間/注目度の指標.csv（00b_注目度の指標.py。日経の報道・事前報道・株探の記事数・売買代金・合成注目度）
#   ../data/prices/{案件}.csv・../data_old/prices/{案件}.csv（日次の株価。60営業日前基準のプレミアムに使う）
# 出力ファイル
#   結果/注目度.csv（同じ内容を1行ずつ画面にも出す）
#
# 実行方法
#   python3 04_注目度.py
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf, warnings; warnings.filterwarnings('ignore')
from scipy import stats
import os; B = '../'; H = os.environ.get('SAIGEN', B + '再現') + '/'
if 'SAIGEN' in os.environ: B = H   # Colab などで環境変数 SAIGEN を使う場合は、株価も同じ場所に置く
A = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str})
# 日経_事後＝公表後の日経の報道件数、事前報道あり＝事前報道の有無、合成注目度＝合成注目度（00b が作る列名）
T = pd.read_csv(H + '中間/注目度の指標.csv', index_col=0)[['日経_事後', '事前報道あり', '合成注目度', 'log売買代金']]
S = A[A.post20_pp.notna() & A.sp.notna()].join(T, rsuffix='_t'); S['nk'] = S.日経_事後 > 0
rows = []
def put(sec, lab, **k): rows.append({'節': sec, '項目': lab, **k}); print(sec, lab, k)   # 結果の表に1行足し、画面にも出す
# 注目度①：収益を価格差と部分買付けで回帰した残差の絶対値を、日経の報道の有無で比べる（Mann-Whitney の U 検定）
X = sm.add_constant(S[['sp', 'PG_部分買付け']].astype(float)); S['ares'] = (S.post20_pp - sm.OLS(S.post20_pp, X).fit().predict(X)).abs()
put('注目度①', '説明できない部分の絶対値の平均（報道なし／あり）', 報道なし=round(S[~S.nk].ares.mean(), 2), 報道あり=round(S[S.nk].ares.mean(), 2), p=round(stats.mannwhitneyu(S[S.nk].ares, S[~S.nk].ares).pvalue, 4), 件数=f'{int((~S.nk).sum())}/{int(S.nk.sum())}')
def eff(sub, v):
    """標本 sub で、収益を条件 v・価格差・部分買付けに回帰し、v の（係数, p 値, 該当件数）を返す。標準誤差は HC1。"""
    x = sub[[v, 'sp', 'PG_部分買付け']].astype(float); r = sm.OLS(sub.post20_pp, sm.add_constant(x)).fit(cov_type='HC1'); return round(r.params[v], 2), round(r.pvalues[v], 3), int(x[v].sum())
for v, lab in [('PG_入札競合', '入札・競合あり'), ('PG_親子上場', '親子上場の解消'), ('PG_優待廃止', '株主優待の廃止')]:
    put('注目度①', f'{lab}の効果（報道なし／あり）', 報道なし=eff(S[~S.nk], v), 報道あり=eff(S[S.nk], v))
# 注目度②：価格差2%超の部分買付けを、合成注目度が標本全体の中央値以下か超かで分けて平均収益を比べる（Welch の t 検定）
hi = S[(S.PG_部分買付け == 1) & (S.sp > 2)]; lo = hi.合成注目度 <= S.合成注目度.median()
put('注目度②', '部分買付け・価格差2%超の20営業日収益（注目度 低／高）', 低=round(hi[lo].post20_pp.mean(), 2), 高=round(hi[~lo].post20_pp.mean(), 2), p=round(stats.ttest_ind(hi[lo].post20_pp, hi[~lo].post20_pp, equal_var=False).pvalue, 3), 件数=f'{int(lo.sum())}/{int((~lo).sum())}', 順位相関=round(stats.spearmanr(hi.合成注目度, hi.post20_pp)[0], 2))
# 注目度③：プレミアム（買付価格÷J の前営業日の終値−1。公表が取引終了後の多くの案件では公表日の終値が基準になる）を
# 売買代金の対数に中央値回帰する。統制変数を変えて頑健性も見る
S['p'] = S.premium * 100; S['post'] = S.date >= '2023-08-31'   # post＝2023年8月31日の経済産業省の指針以降
for ctrl, nm in [('log_mktcap', '時価総額'), ('log_mktcap + PG_fund + PG_mbo', '時価総額・ファンド・MBO'), ('log_mktcap + PG_fund + PG_mbo + PG_部分買付け', '時価総額・ファンド・MBO・部分買付け')]:
    for sub, g in [(S, '全体'), (S[S.post], '指針後')]:
        r = smf.quantreg('p ~ log売買代金 + ' + ctrl, sub.dropna(subset=['p', 'log売買代金', 'log_mktcap'])).fit(q=.5)
        put('注目度③', f'売買代金（対数）の係数｜統制：{nm}｜{g}', 係数=round(r.params['log売買代金'], 2), p=round(r.pvalues['log売買代金'], 3), 件数=int(r.nobs))
pd.DataFrame(rows).to_csv(H + '結果/注目度.csv', index=False, encoding='utf-8-sig')
# 注目度③（続き）：上のプレミアム（表では「公表日終値基準」と呼ぶ）と、60営業日前の終値を基準としたプレミアムの中央値を、
# 事前報道の有無と平常時の売買代金の大小で分けて比べる。60営業日前の基準は、公表前の思惑で株価が上がった分を含めて見るためである。
# 以前の版（attention/check2.py・fig_cde.py。このリポジトリには含めていない）は買付価格を1日ずれた終値から逆算していたため、ここで計算し直している。
import glob
def p60(k):
    """案件 k の、公表日から60営業日前の終値を基準としたプレミアム（比率）を返す。株価が足りなければ欠損値。

    分子の買付価格は 公表日の終値×(1＋premium) で求める（原文の買付価格と一致することは 05_買付価格の照合.py で確認している）。
    """
    f = (glob.glob(B + f'data/prices/{k}.csv') + glob.glob(B + f'data_old/prices/{k}.csv'))
    if not f: return np.nan
    p = pd.read_csv(f[0]); ix = p.index[p.date <= k.split('_')[1]]
    if len(ix) <= 60: return np.nan
    c0, c60 = p.close.iloc[ix[-1]], p.close.iloc[ix[-1] - 60]
    return c0 * (1 + S.loc[k, 'premium']) / c60 - 1
S['p60'] = [100 * p60(k) for k in S.index]
med = S.log売買代金.median(); S['grp'] = np.where(S.事前報道あり == 1, '事前報道あり', np.where(S.log売買代金 > med, '平常の売買代金 大', '平常の売買代金 小'))
for g, d in S.groupby('grp'):
    put('注目度③', f'プレミアムの中央値（{g}）', 公表日終値基準=round(d.p.median(), 1), 六十営業日前基準=round(d.p60.median(), 1), 件数=len(d))
nb = S[S.事前報道あり == 0]; hi_, lo_ = nb[nb.log売買代金 > med], nb[nb.log売買代金 <= med]
put('注目度③', '売買代金 大／小（事前報道なし）の差の検定', 公表日終値基準p=round(stats.mannwhitneyu(hi_.p, lo_.p).pvalue, 3), 六十営業日前基準p=round(stats.mannwhitneyu(hi_.p60.dropna(), lo_.p60.dropna()).pvalue, 3))
pd.DataFrame(rows).to_csv(H + '結果/注目度.csv', index=False, encoding='utf-8-sig')
