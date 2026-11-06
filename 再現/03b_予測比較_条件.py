# 予測誤差の比較（論文の表の版）：① 数値のみ／② 数値＋感情指標／E 数値＋書類の条件（全案件）／F 数値＋書類の条件（価格が自由に動いた全部買付けだけ）
#   書類の条件＝プログラム判定の11変数。部分買付けは変数にせず、予測の起点を変える（部分買付けなら起点0）。他の10変数を変数として足す
#   （買付者がファンド・MBO は「数値」の buy_fund・buy_mbo としてすでに入っている＝プログラム判定）
#   F：10変数に「価格が自由に動いた全部買付け」（張り付きでも部分買付けでもない）の0/1を掛けて足す。E が悪化したのを見てから加えた設計（探索的）
#   参考 D：数値＋部分買付けの起点だけ（改善の大部分がどこから来るかの説明用。表には載せない）
# 使い方：python3 03b_予測比較_条件.py post20   … 目的変数＝J+2〜J+21 の超過収益（従来）
#         python3 03b_予測比較_条件.py W1       … 目的変数＝J+2〜届出書の当初の買付期間の末日 の超過収益（延長は見ない。00c_買付期間末日.py）
#         python3 03b_予測比較_条件.py R1       … 論文の主結果：同じ期間の株価そのものの保有収益（市場を引かない。00c_買付期間末日.py）
# 手順（分割・前処理・Ridge・候補の選び方）は 03_予測比較.py と同じ
import sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from sklearn.linear_model import Ridge
import os; H = os.environ.get('SAIGEN', '../再現') + '/'; sys.path.insert(0, H); import model
TGT = sys.argv[1] if len(sys.argv) > 1 else 'post20'
d = pd.read_csv(H + '中間/分析表_413.csv', index_col=0, dtype={'code': str}, keep_default_na=False)
meta = json.load(open(H + '入力/prepared_data.json')); NUM = meta['FE13'] + meta['POST_EXTRA']; CONT = meta['CONTINUOUS']
SENT = ['新闻标题语气', '新闻标题数', '意見表明語気']
PG = ['PG_入札競合', 'PG_没提价', 'PG_大株主契約なし', 'PG_取締役会中立', 'PG_許認可待ち', 'PG_自己資金', 'PG_優待廃止', 'PG_親子上場']
d['部分買付け'], d['buy_fund'], d['buy_mbo'] = d['PG_部分买付'], d['PG_fund'], d['PG_mbo']
for c in NUM + SENT + PG + ['post20_pp', 'post20_raw', 'n_post20', '部分買付け', 'pinned', 'W1_期间内', 'buy_fund', 'buy_mbo']: d[c] = pd.to_numeric(d[c], errors='coerce')
d['部分買付け'] = d['部分買付け'].fillna(0)
if TGT in ('W1', 'R1'):
    T = pd.read_csv(H + '中間/買付期間末日.csv', index_col=0, keep_default_na=False)   # 00c_買付期間末日.py
    d['y_raw'] = pd.to_numeric(T[TGT + '_raw'].reindex(d.index), errors='coerce'); d['y_end'] = T.label_end_W1.reindex(d.index).astype(str)
    ok = d.y_raw.notna() & d.y_end.str.len().eq(10)
else:
    d['y_raw'] = d.post20_raw; d['y_end'] = d.label_end_post.astype(str); ok = (d.n_post20 == 20) & d.y_raw.notna()
d['y_pp'] = 100 * np.log1p(d.y_raw / 100)
free = ((d.pinned.fillna(0) == 0) & (d['部分買付け'] == 0)).astype(float)
for c in PG + ['buy_fund', 'buy_mbo']: d['F_' + c] = d[c] * free
CANDS = [['standard', 1], ['standard', 10], ['standard', 100], ['robust', 1], ['robust', 10], ['robust', 100]]
def make_folds():
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
    v = 100 * np.log1p(x.spread_J1.fillna(0).clip(lower=0).to_numpy()); return v * (1 - x['部分買付け'].to_numpy()) if adj else v
def fit(Tr, num, adj, c):
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
        sc = [np.mean(np.concatenate([pr(x, v, c) - v.y_pp.to_numpy() for x, v in inner if len(v)]) ** 2) for c in CANDS]
        c = CANDS[int(np.argmin(sc))]; pp, m = fit(Tr, num, adj, c); p = m.predict(pp.transform(Va)) + anchor(Va, adj)
        for k, pv in zip(Va.index, p): out.append({'方法': a, '期': fold, 'key': k, '実際': Va.loc[k, 'y_raw'], '予測': 100 * np.expm1(pv / 100), '訓練件数': len(Tr)})
O = pd.DataFrame(out); O['誤差'] = (O.実際 - O.予測).abs(); O.to_csv(H + f'結果/予測_条件_{TGT}.csv', index=False, encoding='utf-8-sig')
rng = np.random.default_rng(0)
def ci(x): x = np.asarray(x); bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(5000)]; return np.round(np.percentile(bs, (2.5, 97.5)), 2)
b1 = O[O.方法 == '① 数値のみ'].set_index('key'); rows = []
print(f'==== 目的変数 {TGT}｜評価 {len(b1)} 件｜各期の訓練件数', O.groupby('期').訓練件数.first().to_dict())
for g in ARMS:
    e = O[O.方法 == g].set_index('key').reindex(b1.index); diff = b1.誤差 - e.誤差; lo, hi = ci(diff)
    print(f'{g:28s} 平均誤差 {e.誤差.mean():.2f}｜①より1件あたり {diff.mean():+.2f} 小さい（95%区間 {lo}〜{hi}）')
    rows.append({'方法': g, '平均誤差': round(e.誤差.mean(), 2), '①との差': round(diff.mean(), 2), '95%下限': lo, '95%上限': hi})
pd.DataFrame(rows).to_csv(H + f'結果/予測_要約_条件_{TGT}.csv', index=False, encoding='utf-8-sig')
