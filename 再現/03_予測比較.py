# 03_予測比較.py：20営業日の超過収益の予測誤差を、使う情報の違う4つの方法で比べる（以前の版の予測比較）
#
# 目的
#   以前の版の論文で報告した予測比較（目的変数＝J+2〜J+21 の TOPIX を引いた超過収益 post20）を再現する。
#   現在の論文の予測比較は 03b_予測比較_条件.py R1 が作る。このファイルは 全部実行.sh からは呼ばれない。
#
# 比べる方法（予測の起点＝価格差の対数。モデルは起点からのずれを予測する）
#   ① 数値のみ（市場区分・時価総額などの数値変数）
#   ② 数値＋従来の感情指標
#   ③ 数値＋取引構造：部分買付けなら起点を0にする（部分買付けでは買付価格まで株価が上がるとは限らないため）
#   ④ 起点は変えず、部分買付けの有無と「部分買付け×価格差」を変数として足す
#   モデルは Ridge 回帰（L2 罰則付きの線形回帰）。前処理（standard／robust）と罰則の強さ（1・10・100）は訓練期間の中の検証だけで選ぶ。
#   評価は2024年上期〜2026年上期の半年ごとの5期で行い、各期より前に収益の期間が終わった案件だけで学習する（model.py）。
#
# 入力ファイル
#   中間/分析表_413.csv（引数 プログラム）、中間/旧版の再現用_413.csv（引数 旧。このリポジトリには作成プログラムを含めていない）
#   入力/prepared_data.json（数値変数の一覧）
# 出力ファイル
#   結果/予測_{引数}.csv（案件ごとの予測と誤差）、結果/予測_要約_{引数}.csv（方法ごとの平均誤差と②との差の95%信頼区間）
#
# 実行方法
#   python3 03_予測比較.py プログラム   取引構造・買付者類型ともプログラム（rules.py）の判定を使う
#   python3 03_予測比較.py 旧     以前の版（取引構造を生成AIで判定し、買付価格を修正する前の表）。以前の版の数値 4.65 / 4.81 / 4.01 の再現確認用
#   引数の値「プログラム」はそのまま入力する。
import sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from sklearn.linear_model import Ridge
import os; H = os.environ.get('SAIGEN', '../再現') + '/'; sys.path.insert(0, H); import model
MODE = sys.argv[1] if len(sys.argv) > 1 else 'プログラム'
d = pd.read_csv(H + ('中間/分析表_413.csv' if MODE == 'プログラム' else '中間/旧版の再現用_413.csv'), index_col=0, dtype={'code': str}, keep_default_na=False).rename(columns={'旧_AI_部分买付': '旧_AI_部分買付け'})   # 旧：買付価格を修正する前の表
meta = json.load(open(H + '入力/prepared_data.json')); NUM = meta['FE13'] + meta['POST_EXTRA']; CONT = meta['CONTINUOUS']
SENT = ['報道見出しの語気', '報道見出しの数', '意見表明語気']   # 従来の感情指標（報道見出しの語気・報道見出しの数・意見表明報告書の語気）
src = {'プログラム': ('PG_部分買付け', 'PG_fund', 'PG_mbo'), '旧': ('旧_AI_部分買付け', '旧_buy_fund', '旧_buy_mbo')}[MODE]
d['部分買付け'], d['buy_fund'], d['buy_mbo'] = d[src[0]], d[src[1]], d[src[2]]
for c in NUM + SENT + ['post20_pp', 'post20_raw', 'n_post20', '部分買付け']: d[c] = pd.to_numeric(d[c], errors='coerce')
d['部分買付け'] = d['部分買付け'].fillna(0)   # 価格差のない2件。起点は0になるので、この値は結果に影響しない
d['部分x価格差'] = d['部分買付け'] * 100 * np.log1p(d.spread_J1.fillna(0).clip(lower=0))
CANDS = [['standard', 1], ['standard', 10], ['standard', 100], ['robust', 1], ['robust', 10], ['robust', 100]]   # （前処理, 罰則の強さ）の候補
def make_folds():
    """評価の5期それぞれについて（期の名前, 訓練データ, 評価データ, 訓練内の検証分割）を返す。

    評価データ＝その期に J がある案件。訓練データ＝その期の開始より前に20営業日の期間が終わった案件で、評価データと同じ会社を除く。
    """
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
    """予測の起点＝100×ln(1＋価格差)（価格差が負なら0）。adj が真なら部分買付けの起点を0にする（方法③）。"""
    v = 100 * np.log1p(x.spread_J1.fillna(0).clip(lower=0).to_numpy()); return v * (1 - x['部分買付け'].to_numpy()) if adj else v
def fit(Tr, num, adj, c):
    """訓練データ Tr で前処理を当てはめ、起点からのずれ（収益−起点）を Ridge で学習する。c＝（前処理, 罰則の強さ）。"""
    pp = model.Prep(num, [], c[0], CONT + [x for x in num if x not in NUM]).fit(Tr)
    return pp, Ridge(alpha=c[1]).fit(pp.transform(Tr), Tr.post20_pp.to_numpy() - anchor(Tr, adj))
ARMS = {'① 数値のみ': (NUM, False), '② 数値＋感情指標': (NUM + SENT, False), '③ 数値＋取引構造（起点を変える）': (NUM, True), '④ 数値＋部分買付け・交差項': (NUM + ['部分買付け', '部分x価格差'], False)}
out = []
for fold, Tr, Va, inner in make_folds():
    for a, (num, adj) in ARMS.items():
        def pr(x, v, c): pp, m = fit(x, num, adj, c); return m.predict(pp.transform(v)) + anchor(v, adj)
        # 訓練期間の中の検証で二乗誤差が最も小さい候補を選び、訓練データ全体で学習し直して評価期を予測する
        sc = [np.mean(np.concatenate([pr(x, v, c) - v.post20_pp.to_numpy() for x, v in inner if len(v)]) ** 2) for c in CANDS]
        c = CANDS[int(np.argmin(sc))]; pp, m = fit(Tr, num, adj, c); p = m.predict(pp.transform(Va)) + anchor(Va, adj)
        for k, pv in zip(Va.index, p): out.append({'方法': a, '期': fold, 'key': k, '実際': Va.loc[k, 'post20_raw'], '予測': 100 * np.expm1(pv / 100), '張り付き': Va.loc[k, 'pinned'], '候補': f'{c[0]}|{c[1]}', '訓練件数': len(Tr)})
O = pd.DataFrame(out); O['誤差'] = (O.実際 - O.予測).abs(); O.to_csv(H + f'結果/予測_{MODE}.csv', index=False, encoding='utf-8-sig')   # 誤差＝実際の収益と予測の差の絶対値（%）
rng = np.random.default_rng(0)
def ci(x, q=(2.5, 97.5)):   # 案件を復元抽出するブートストラップ（5000回）で、平均の95%信頼区間を求める
    x = np.asarray(x); bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(5000)]; return np.round(np.percentile(bs, q), 2)
b1 = O[O.方法 == '① 数値のみ'].set_index('key'); b2 = O[O.方法 == '② 数値＋感情指標'].set_index('key'); rows = []
print(f'==== {MODE}｜評価 {len(b1)} 件｜各期の訓練件数', O.groupby('期').訓練件数.first().to_dict())
for g in ARMS:
    e = O[O.方法 == g].set_index('key').reindex(b1.index); diff = b2.誤差 - e.誤差; lo, hi = ci(diff)
    print(f'{g:22s} 平均誤差 {e.誤差.mean():.2f}｜①との比 {(e.誤差.mean() / b1.誤差.mean() - 1) * 100:+.0f}%｜②より1件あたり {diff.mean():+.2f} 小さい（95%信頼区間 {lo}〜{hi}）')
    rows.append({'方法': g, '平均誤差': round(e.誤差.mean(), 2), '②との差': round(diff.mean(), 2), '95%下限': lo, '95%上限': hi})
pd.DataFrame(rows).to_csv(H + f'結果/予測_要約_{MODE}.csv', index=False, encoding='utf-8-sig')
