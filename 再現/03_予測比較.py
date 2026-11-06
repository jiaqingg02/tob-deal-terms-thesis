# その後20営業日の収益の予測誤差を3つの方法で比べる（論文 p.24）。手順は mechanism_idx/old_main.py と同じ
#   ① 数値のみ  ② 数値＋従来の感情指標  ③ 数値＋書類の取引構造（部分買付けなら起点を0にする）  ④ 起点は変えず、部分買付けと「部分買付け×価格差」を変数に足す
#   予測の起点＝価格差（対数）。モデル＝Ridge、前処理と罰則の強さは訓練期間の中だけで選ぶ。評価＝2024年上期〜2026年上期の5期（各期より前に終わった案件だけで学習）
# 使い方：python3 03_予測比較.py 程序   … 取引構造・買付者類型ともプログラム判定（論文の版）
#         python3 03_予測比較.py 旧     … 以前の版（生成AIの取引構造・買付者類型の旧ラベル・買付価格の修正前。01b_旧版の再現用.py の表）。論文の旧数値 4.65 / 4.81 / 4.01 の再現確認用
import sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from sklearn.linear_model import Ridge
import os; H = os.environ.get('SAIGEN', '../再現') + '/'; sys.path.insert(0, H); import model
MODE = sys.argv[1] if len(sys.argv) > 1 else '程序'
d = pd.read_csv(H + ('中間/分析表_413.csv' if MODE == '程序' else '中間/旧版の再現用_413.csv'), index_col=0, dtype={'code': str}, keep_default_na=False)   # 旧：買付価格の修正前
meta = json.load(open(H + '入力/prepared_data.json')); NUM = meta['FE13'] + meta['POST_EXTRA']; CONT = meta['CONTINUOUS']
SENT = ['新闻标题语气', '新闻标题数', '意見表明語気']
src = {'程序': ('PG_部分买付', 'PG_fund', 'PG_mbo'), '旧': ('旧_AI_部分买付', '旧_buy_fund', '旧_buy_mbo')}[MODE]
d['部分買付け'], d['buy_fund'], d['buy_mbo'] = d[src[0]], d[src[1]], d[src[2]]
for c in NUM + SENT + ['post20_pp', 'post20_raw', 'n_post20', '部分買付け']: d[c] = pd.to_numeric(d[c], errors='coerce')
d['部分買付け'] = d['部分買付け'].fillna(0)   # 価格差のない2件（起点は0になるので値は結果に影響しない）
d['部分x価差'] = d['部分買付け'] * 100 * np.log1p(d.spread_J1.fillna(0).clip(lower=0))
CANDS = [['standard', 1], ['standard', 10], ['standard', 100], ['robust', 1], ['robust', 10], ['robust', 100]]
def make_folds():
    s = d[(d.avail_post == 'ok') & (d.n_post20 == 20) & d.post20_raw.notna()].copy()
    s['jump_day'] = s.jump_day.astype(str).str[:10]; s['label_end_post'] = s.label_end_post.astype(str)
    out = []
    for fold, lo, hi in model.OUTER:
        te = s[s.jump_day.ge(lo) & s.jump_day.lt(hi)]; tr = s[s.label_end_post.lt(lo) & ~s.code.isin(te.code)]
        if len(tr) < model.MIN_TRAIN or len(te) < model.MIN_TEST: continue
        sp = model.inner_splits(tr, 'label_end_post')
        if sp: out.append((fold, tr, te, sp))
    return out
def anchor(x, adj):
    v = 100 * np.log1p(x.spread_J1.fillna(0).clip(lower=0).to_numpy()); return v * (1 - x['部分買付け'].to_numpy()) if adj else v
def fit(Tr, num, adj, c):
    pp = model.Prep(num, [], c[0], CONT + [x for x in num if x not in NUM]).fit(Tr)
    return pp, Ridge(alpha=c[1]).fit(pp.transform(Tr), Tr.post20_pp.to_numpy() - anchor(Tr, adj))
ARMS = {'① 数値のみ': (NUM, False), '② 数値＋感情指標': (NUM + SENT, False), '③ 数値＋取引構造（起点を変える）': (NUM, True), '④ 数値＋部分買付け・交差項': (NUM + ['部分買付け', '部分x価差'], False)}
out = []
for fold, Tr, Va, inner in make_folds():
    for a, (num, adj) in ARMS.items():
        def pr(x, v, c): pp, m = fit(x, num, adj, c); return m.predict(pp.transform(v)) + anchor(v, adj)
        sc = [np.mean(np.concatenate([pr(x, v, c) - v.post20_pp.to_numpy() for x, v in inner if len(v)]) ** 2) for c in CANDS]
        c = CANDS[int(np.argmin(sc))]; pp, m = fit(Tr, num, adj, c); p = m.predict(pp.transform(Va)) + anchor(Va, adj)
        for k, pv in zip(Va.index, p): out.append({'方法': a, '期': fold, 'key': k, '実際': Va.loc[k, 'post20_raw'], '予測': 100 * np.expm1(pv / 100), '張り付き': Va.loc[k, 'pinned'], '候補': f'{c[0]}|{c[1]}', '訓練件数': len(Tr)})
O = pd.DataFrame(out); O['誤差'] = (O.実際 - O.予測).abs(); O.to_csv(H + f'結果/予測_{MODE}.csv', index=False, encoding='utf-8-sig')
rng = np.random.default_rng(0)
def ci(x, q=(2.5, 97.5)): x = np.asarray(x); bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(5000)]; return np.round(np.percentile(bs, q), 2)
b1 = O[O.方法 == '① 数値のみ'].set_index('key'); b2 = O[O.方法 == '② 数値＋感情指標'].set_index('key'); rows = []
print(f'==== {MODE}｜評価 {len(b1)} 件｜各期の訓練件数', O.groupby('期').訓練件数.first().to_dict())
for g in ARMS:
    e = O[O.方法 == g].set_index('key').reindex(b1.index); diff = b2.誤差 - e.誤差; lo, hi = ci(diff)
    print(f'{g:22s} 平均誤差 {e.誤差.mean():.2f}｜①比 {(e.誤差.mean() / b1.誤差.mean() - 1) * 100:+.0f}%｜②より1件あたり {diff.mean():+.2f} 小さい（95%区間 {lo}〜{hi}）')
    rows.append({'方法': g, '平均誤差': round(e.誤差.mean(), 2), '②との差': round(diff.mean(), 2), '95%下限': lo, '95%上限': hi})
pd.DataFrame(rows).to_csv(H + f'結果/予測_要約_{MODE}.csv', index=False, encoding='utf-8-sig')
