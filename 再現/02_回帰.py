# 02_回帰.py：取引条件ごとに、公表後の収益への効果を回帰で推定する（論文の主な結果）
#
# 目的
#   論文の主な結果の表（部分買付けの平均収益、取引条件の係数、張り付いた案件での反証、2023年8月の経済産業省の指針の後）を作る。
#   論文に載せるのは引数 R1 の結果である。
#
# 目的変数（引数で選ぶ）
#   R1（主結果）  J+1 の終値から当初の買付期間の末日の終値までの、株価そのものの保有収益。
#                 R1＝100×(末日の終値 ÷ J+1 の終値 − 1)。市場を引かず、回帰では 100×ln(1＋R1/100) を使い、年ダミーで時期の違いを統制する。
#                 Hsieh and Walkling (2005) と同じ扱いである。
#   W1（確認用）  同じ期間の、TOPIX を引いた超過収益（年ダミーなし）
#   post20（引数なし、以前の版）  J+2〜J+21 の20営業日の、TOPIX を引いた超過収益
#   ここで J＝公表後最初の取引日、J+1＝その次の取引日である。R1・W1 は 00c_買付期間末日.py が計算する。
#
# 入力ファイル
#   中間/分析表_413.csv（01_分析表.py）、中間/買付期間末日.csv（00c_買付期間末日.py。R1・W1 のときだけ）
# 出力ファイル
#   結果/回帰_R1.csv（引数 R1）、結果/回帰_W1.csv（引数 W1）、結果/回帰.csv（引数なし）。同じ表を画面にも出す
#
# 処理の流れ
#   標本を3つに分ける：部分買付け／張り付いた全部買付け（|価格差|≦1%）／自由に動く全部買付け（それ以外の全部買付け）。
#   ① 部分買付け：価格差2%超と2%以下に分け、それぞれ平均収益が0と異なるかを t 検定する。
#   ② 公開買付届出書の条件：自由に動く全部買付けと全体で、次の回帰の「条件の有無」の係数を見る。
#        収益（対数、%）＝定数＋効果×条件の有無＋係数×価格差（＋全体では部分買付けの有無）（＋R1 では年ダミー）
#      標準誤差は HC1（不均一分散に頑健な標準誤差）、有意水準は10%（*）と5%（**）である。
#   ③ 意見表明報告書の条件（株主優待の廃止・親子上場の解消）：全体・全部買付け・自由に動く全部買付けで同じ回帰を行う。
#   ④ 張り付いた全部買付け：株価が買付価格に張り付いていれば条件の効果は出ないはずなので、反証として同じ回帰を行う。
#   ⑤ ①〜④を2023年8月31日（経済産業省「企業買収における行動指針」の公表日）以降の案件だけで繰り返す。
#
# 実行方法
#   python3 02_回帰.py R1   （論文の主結果）
#   python3 02_回帰.py W1   （TOPIX を引いた超過収益での確認）
#   python3 02_回帰.py      （以前の版の20営業日の超過収益）
#   Google Colab などで置き場所が違う場合は、環境変数 SAIGEN に 再現/ フォルダのパスを入れる。
import numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy import stats
import os; H = os.environ.get('SAIGEN', '../再現') + '/'   # 置き場所は環境変数 SAIGEN で変えられる
A = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str})
import sys; TGT = sys.argv[1] if len(sys.argv) > 1 else 'post20'   # 目的変数の選択（冒頭の説明を参照）
if TGT == 'W1':
    W = pd.read_csv(H + '中間/買付期間末日.csv', index_col=0, keep_default_na=False)
    A['y'] = 100 * np.log1p(pd.to_numeric(W.W1_raw.reindex(A.index), errors='coerce') / 100)
elif TGT == 'R1':
    W = pd.read_csv(H + '中間/買付期間末日.csv', index_col=0, keep_default_na=False)
    A['y'] = 100 * np.log1p(pd.to_numeric(W.R1_raw.reindex(A.index), errors='coerce') / 100)
else: A['y'] = A.post20_pp
YD = TGT == 'R1'   # R1 は市場を引かないため、年ダミーで時期ごとの市場全体の動きを統制する
S = A[A.y.notna() & A.sp.notna()].copy()        # 収益と価格差の両方がある案件（post20 では411件）
# 取引条件の列名と表に出す名前。PG_ は program_vars/rules.py による判定（0/1）を表す
ITEMS = [('PG_入札競合', '入札・競合あり'), ('PG_値上げなし', '交渉で値上げされていない'), ('PG_fund', '買付者がファンド'), ('PG_mbo', 'MBO'),
         ('PG_大株主契約なし', '大株主の応募契約なし'), ('PG_取締役会中立', '取締役会が中立'), ('PG_許認可待ち', '許認可の承認待ち'), ('PG_自己資金', '自己資金')]
IKV = [('PG_優待廃止', '株主優待の廃止'), ('PG_親子上場', '親子上場の解消')]   # 意見表明報告書から判定する条件
def reg(sub, v, ctrl=()):
    """標本 sub で、収益 y を条件 v・価格差 sp・統制変数 ctrl（R1 では年ダミーも）に回帰し、v の係数と p 値を返す。

    条件に該当する案件か該当しない案件が2件未満のときは推定しない（係数・p 値は欠損値）。
    """
    sub = sub[sub[v].notna()]; x = sub[[v, 'sp'] + list(ctrl)].astype(float); k = int((x[v] != 0).sum())
    if YD: x = x.join(pd.get_dummies(sub.date.astype(str).str[:4], prefix='年', drop_first=True).astype(float))   # 標本の中で最も早い年を基準とする
    if k < 2 or len(sub) - k < 2: return dict(係数=np.nan, p=np.nan, 該当件数=k, 対象件数=len(sub))
    r = sm.OLS(sub.y.astype(float), sm.add_constant(x)).fit(cov_type='HC1')
    return dict(係数=round(r.params[v], 4), p=round(r.pvalues[v], 4), 該当件数=k, 対象件数=len(sub))
rows = []
def put(sec, lab, r): rows.append({'節': sec, '項目': lab, **r, '有意': '**' if r['p'] < .05 else '*' if r['p'] < .1 else ''})   # 結果の表に1行足す
def story(S, tag):
    """標本 S について①〜④の結果を順に計算し、表の行に足す。tag は節の名前の頭に付ける文字（⑤では「⑤指針後 」）。"""
    pb, pin = S.PG_部分買付け == 1, S.pinned == 1; F, FP = S[~pb & ~pin], S[~pb & pin]   # F＝自由に動く全部買付け、FP＝張り付いた全部買付け
    hi, lo = S[pb & (S.sp > 2)], S[pb & (S.sp <= 2)]
    put(f'{tag}① 部分買付け', '価格差2%超の平均（0と比較）', dict(係数=round(hi.y.mean(), 4), p=round(stats.ttest_1samp(hi.y, 0).pvalue, 4), 該当件数=len(hi), 対象件数=int(pb.sum())))
    put(f'{tag}① 部分買付け', '価格差2%以下の平均（0と比較）', dict(係数=round(lo.y.mean(), 4), p=round(stats.ttest_1samp(lo.y, 0).pvalue, 4), 該当件数=len(lo), 対象件数=int(pb.sum())))
    w = hi['W1_以前の計算'].dropna()
    # 以前の版（post20）でだけ、価格差2%超の部分買付けについて買付期間中の超過収益の平均も出す
    if TGT == 'post20': put(f'{tag}① 部分買付け', '価格差2%超・買付期間中の平均', dict(係数=round(w.mean(), 4), p=round(stats.ttest_1samp(w, 0).pvalue, 4), 該当件数=len(w), 対象件数=int(pb.sum())))
    for v, lab in ITEMS: put(f'{tag}② 価格が自由に動いた全部買付け', lab, reg(F, v))
    for v, lab in ITEMS[:4]: put(f'{tag}② 全体', lab, reg(S, v, ['PG_部分買付け']))
    for v, lab in IKV:
        put(f'{tag}③ 全体', lab, reg(S, v, ['PG_部分買付け'])); put(f'{tag}③ 全部買付け', lab, reg(S[~pb], v)); put(f'{tag}③ 価格が自由に動いた全部買付け', lab, reg(F, v))
    for v, lab in ITEMS[:4]: put(f'{tag}④ 張り付いた全部買付け', lab, reg(FP, v))
story(S, '')
story(S[S.date >= '2023-08-31'], '⑤指針後 ')
R = pd.DataFrame(rows); R.to_csv(H + ('結果/回帰.csv' if TGT == 'post20' else f'結果/回帰_{TGT}.csv'), index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200); print(f'標本 {len(S)} 件（目的変数 {TGT}）'); print(R.to_string(index=False))
