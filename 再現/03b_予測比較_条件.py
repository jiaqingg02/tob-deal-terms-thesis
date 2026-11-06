# 03b_予測比較_条件.py：「価格差だけ」の予測と「取引条件を加えた」予測の誤差を比べる（論文の予測比較の表）
#
# 目的
#   論文の予測比較の表を作る。論文に載せるのは引数 R1 の結果である。
#   予測の起点は価格差の対数であり、モデルは起点からのずれを予測する。比べる方法は次のとおり。
#     ① 数値のみ（市場区分・時価総額などの数値変数。買付者がファンド・MBO の判定 buy_fund・buy_mbo もここに入る）
#     ② 数値＋従来の感情指標
#     E  数値＋取引条件（全案件）：部分買付けなら起点を0にし、残りの取引条件（PG に並べた8項目）を変数として足す
#     F  数値＋取引条件（自由に動く全部買付けだけ）：E と同じく起点を変え、8項目と buy_fund・buy_mbo に
#        「自由に動く全部買付け（張り付きでも部分買付けでもない）なら1」を掛けた変数を足す。
#        E で誤差が大きくなったのを見てから加えた設計であり、探索的な結果である。
#     参考D  数値＋部分買付けの起点の変更だけ（改善の大部分がどこから来るかを説明するためのもので、表には載せない）
#   取引条件はすべて program_vars/rules.py による判定（PG_ で始まる列）であり、生成AIは使わない。
#
# 目的変数（引数で選ぶ）
#   R1（主結果）  J+1 の終値から当初の買付期間の末日の終値までの、株価そのものの保有収益（市場を引かない。00c_買付期間末日.py）
#   W1（確認用）  同じ期間の、TOPIX を引いた超過収益（買付期間の延長は見ない）
#   post20       J+2〜J+21 の20営業日の、TOPIX を引いた超過収益（以前の版。引数なしのときもこれ）
#   どれも 100×ln(1＋収益/100) に直して学習し、予測を%に戻して誤差を測る。
#
# 手順
#   データの分割・前処理・Ridge 回帰・候補の選び方は 03_予測比較.py と同じである（model.py）。
#   評価は2024年上期〜2026年上期の半年ごとの5期で、各期の開始より前に収益の期間が終わった案件だけで学習する。
#   各方法の平均誤差（実際と予測の差の絶対値の平均、%）と、①との差の95%信頼区間（ブートストラップ）を出す。
#
# 入力ファイル
#   中間/分析表_413.csv（01_分析表.py）、中間/買付期間末日.csv（00c_買付期間末日.py。R1・W1 のとき）、入力/prepared_data.json
# 出力ファイル
#   結果/予測_条件_{引数}.csv（案件ごとの予測と誤差）、結果/予測_要約_条件_{引数}.csv（方法ごとの要約）
#
# 実行方法
#   python3 03b_予測比較_条件.py R1       （論文の主結果）
#   python3 03b_予測比較_条件.py W1
#   python3 03b_予測比較_条件.py post20
import sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from sklearn.linear_model import Ridge
import os; H = os.environ.get('SAIGEN', '../再現') + '/'; sys.path.insert(0, H); import model
TGT = sys.argv[1] if len(sys.argv) > 1 else 'post20'
d = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str}, keep_default_na=False)
meta = json.load(open(H + '入力/prepared_data.json')); NUM = meta['FE13'] + meta['POST_EXTRA']; CONT = meta['CONTINUOUS']
SENT = ['報道見出しの語気', '報道見出しの数', '意見表明語気']   # 従来の感情指標（報道見出しの語気・報道見出しの数・意見表明報告書の語気）
# 部分買付け・ファンド・MBO 以外の取引条件8項目
PG = ['PG_入札競合', 'PG_値上げなし', 'PG_大株主契約なし', 'PG_取締役会中立', 'PG_許認可待ち', 'PG_自己資金', 'PG_優待廃止', 'PG_親子上場']
d['部分買付け'], d['buy_fund'], d['buy_mbo'] = d['PG_部分買付け'], d['PG_fund'], d['PG_mbo']
for c in NUM + SENT + PG + ['post20_pp', 'post20_raw', 'n_post20', '部分買付け', 'pinned', 'W1_以前の計算', 'buy_fund', 'buy_mbo']: d[c] = pd.to_numeric(d[c], errors='coerce')
d['部分買付け'] = d['部分買付け'].fillna(0)
if TGT in ('W1', 'R1'):
    T = pd.read_csv(H + '中間/買付期間末日.csv', index_col=0, keep_default_na=False)   # 00c_買付期間末日.py の出力
    # y_end＝収益の期間の最終日（当初の買付期間の末日）。訓練データの選別に使う
    d['y_raw'] = pd.to_numeric(T[TGT + '_raw'].reindex(d.index), errors='coerce'); d['y_end'] = T.label_end_W1.reindex(d.index).astype(str)
    ok = d.y_raw.notna() & d.y_end.str.len().eq(10)
else:
    d['y_raw'] = d.post20_raw; d['y_end'] = d.label_end_post.astype(str); ok = (d.n_post20 == 20) & d.y_raw.notna()
d['y_pp'] = 100 * np.log1p(d.y_raw / 100)
free = ((d.pinned.fillna(0) == 0) & (d['部分買付け'] == 0)).astype(float)   # 自由に動く全部買付けなら1
for c in PG + ['buy_fund', 'buy_mbo']: d['F_' + c] = d[c] * free
CANDS = [['standard', 1], ['standard', 10], ['standard', 100], ['robust', 1], ['robust', 10], ['robust', 100]]   # （前処理, 罰則の強さ）の候補
def make_folds():
    """評価の5期それぞれについて（期の名前, 訓練データ, 評価データ, 訓練内の検証分割）を返す。

    評価データ＝その期に J がある案件。訓練データ＝その期の開始より前に収益の期間（y_end）が終わった案件で、評価データと同じ会社を除く。
    """
    s = d[(d.avail_post == 'ok') & ok].copy()
    s['jump_day'] = s.jump_day.astype(str).str[:10]
    out = []
    for fold, lo, hi in model.OUTER:
        te = s[s.jump_day.ge(lo) & s.jump_day.lt(hi)]; tr = s[s.y_end.lt(lo) & ~s.code.isin(te.code)]
        if len(tr) < model.MIN_TRAIN or len(te) < model.MIN_TEST: continue
        sp = model.inner_splits(tr, 'y_end')
        if sp: out.append((fold, tr, te, sp))
    return out
def anchor(x, adj):
    """予測の起点＝100×ln(1＋価格差)（価格差が負なら0）。adj が真なら部分買付けの起点を0にする。"""
    v = 100 * np.log1p(x.spread_J1.fillna(0).clip(lower=0).to_numpy()); return v * (1 - x['部分買付け'].to_numpy()) if adj else v
def fit(Tr, num, adj, c):
    """訓練データ Tr で前処理を当てはめ、起点からのずれ（収益−起点）を Ridge で学習する。c＝（前処理, 罰則の強さ）。"""
    pp = model.Prep(num, [], c[0], CONT + [x for x in num if x not in NUM]).fit(Tr)
    return pp, Ridge(alpha=c[1]).fit(pp.transform(Tr), Tr.y_pp.to_numpy() - anchor(Tr, adj))
ARMS = {'① 数値のみ': (NUM, False), '② 数値＋感情指標': (NUM + SENT, False),
        'E 数値＋書類の条件（全案件）': (NUM + PG, True),
        'F 数値＋書類の条件（自由に動いた全部買付けだけ）': (NUM + ['F_' + c for c in PG + ['buy_fund', 'buy_mbo']], True),
        '参考D 数値＋部分買付けの起点だけ': (NUM, True)}
out = []; FO = make_folds()
for fold, Tr, Va, inner in FO:
    for a, (num, adj) in ARMS.items():
        def pr(x, v, c): pp, m = fit(x, num, adj, c); return m.predict(pp.transform(v)) + anchor(v, adj)
        # 訓練期間の中の検証で二乗誤差が最も小さい候補を選び、訓練データ全体で学習し直して評価期を予測する
        sc = [np.mean(np.concatenate([pr(x, v, c) - v.y_pp.to_numpy() for x, v in inner if len(v)]) ** 2) for c in CANDS]
        c = CANDS[int(np.argmin(sc))]; pp, m = fit(Tr, num, adj, c); p = m.predict(pp.transform(Va)) + anchor(Va, adj)
        for k, pv in zip(Va.index, p): out.append({'方法': a, '期': fold, 'key': k, '実際': Va.loc[k, 'y_raw'], '予測': 100 * np.expm1(pv / 100), '訓練件数': len(Tr)})
O = pd.DataFrame(out); O['誤差'] = (O.実際 - O.予測).abs(); O.to_csv(H + f'結果/予測_条件_{TGT}.csv', index=False, encoding='utf-8-sig')   # 誤差＝実際の収益と予測の差の絶対値（%）
rng = np.random.default_rng(0)
def ci(x):   # 案件を復元抽出するブートストラップ（5000回）で、平均の95%信頼区間を求める
    x = np.asarray(x); bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(5000)]; return np.round(np.percentile(bs, (2.5, 97.5)), 2)
b1 = O[O.方法 == '① 数値のみ'].set_index('key'); rows = []
print(f'==== 目的変数 {TGT}｜評価 {len(b1)} 件｜各期の訓練件数', O.groupby('期').訓練件数.first().to_dict())
for g in ARMS:
    e = O[O.方法 == g].set_index('key').reindex(b1.index); diff = b1.誤差 - e.誤差; lo, hi = ci(diff)
    print(f'{g:28s} 平均誤差 {e.誤差.mean():.2f}｜①より1件あたり {diff.mean():+.2f} 小さい（95%信頼区間 {lo}〜{hi}）')
    rows.append({'方法': g, '平均誤差': round(e.誤差.mean(), 2), '①との差': round(diff.mean(), 2), '95%下限': lo, '95%上限': hi})
pd.DataFrame(rows).to_csv(H + f'結果/予測_要約_条件_{TGT}.csv', index=False, encoding='utf-8-sig')
