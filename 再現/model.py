"""予測比較（03_予測比較.py・03b_予測比較_条件.py）で共通に使う、前処理と時系列のデータ分割。

以前の実験コード（work/processing_experiment/run.py。このリポジトリには含めていない）の Prep・inner_splits・OUTER などを、
処理を一切変えずに写したものである。論文用のフォルダだけで再現できるように、ここに置いている。

主な定数
  OUTER      評価する5期（期の名前, 開始日, 終了日）。2024年上期〜2026年上期の半年ごと。終了日はその日を含まない
  MIN_TRAIN  1期の訓練データに必要な最少件数。これに満たない期は評価しない
  MIN_TEST   1期の評価データに必要な最少件数
  MIN_INNER_TRAIN, MIN_VAL  訓練期間の中の検証分割で必要な訓練・検証の最少件数
  CANDS, N_BOOT, SEED, MAX_PCA, KNOWN_BINS  元の実験コードの設定。03・03b は CANDS を自分で定義しており、これらは使わない
"""
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
CANDS = [(p, a) for p in ('standard', 'robust', 'compressed') for a in (1.0, 10.0, 100.0)]
OUTER = [('2024H1', '2024-01-01', '2024-07-01'), ('2024H2', '2024-07-01', '2025-01-01'),
         ('2025H1', '2025-01-01', '2025-07-01'), ('2025H2', '2025-07-01', '2026-01-01'),
         ('2026H1', '2026-01-01', '2026-07-01')]
MIN_TRAIN, MIN_INNER_TRAIN, MIN_VAL, MIN_TEST = 20, 12, 5, 5
N_BOOT, SEED, MAX_PCA = 3000, 20260928, 3
KNOWN_BINS = [(0, 3, '0-3'), (4, 5, '4-5'), (6, 7, '6-7')]

class Prep:
    """説明変数の前処理。訓練データだけで欠損の補完値と標準化の係数を決め（fit）、同じ変換を評価データにも当てる（transform）。

    num   数値変数の列名
    ai    以前の版で生成AIが作った変数の列名。03・03b では常に空であり、生成AIの変数は使わない
    proc  前処理の方法
            'standard'    欠損を訓練データの中央値で埋め、欠損の有無を示す0/1列を足したうえで、すべての列を標準化する
            'robust'      cont に含まれる連続変数は上下1%で切り詰めてから中央値と四分位範囲で尺度をそろえ、残りの列は標準化する
            'compressed'  ai の変数を主成分分析で最大 MAX_PCA 次元に縮める（ai が空なら 'standard' と同じになる）
    cont  'robust' のときに頑健な尺度化を当てる連続変数の列名
    """
    def __init__(self, num, ai, proc, cont):
        self.num, self.ai, self.proc, self.cont = list(num), list(ai), proc, set(cont)

    def _frame(self, X):
        # 欠損の有無を示す列を足し、欠損を訓練データの中央値で埋める
        Z = X[self.num + self.ai].astype(float).copy()
        for c in self.miss:
            Z[c + '__miss'] = X[c].isna().astype(float)
        return Z.fillna(self.med)

    def fit(self, X):
        base = X[self.num + self.ai].astype(float)
        self.miss = [c for c in self.num + self.ai if base[c].isna().any()]   # 訓練データで欠損がある列だけに欠損の有無の列を作る
        self.med = base.median().fillna(0.0)
        Z = self._frame(X)
        ind = [c + '__miss' for c in self.miss]
        if self.proc == 'robust':
            self.rob = [c for c in self.num + self.ai if c in self.cont]
            self.std = [c for c in Z.columns if c not in self.rob]
            self.lo, self.hi = Z[self.rob].quantile(0.01), Z[self.rob].quantile(0.99)
            self.rs = RobustScaler().fit(Z[self.rob].clip(self.lo, self.hi, axis=1)) if self.rob else None
            self.ss = StandardScaler().fit(Z[self.std])
            self.pca = None
        elif self.proc == 'compressed' and self.ai:
            self.std = self.num + ind
            self.ss = StandardScaler().fit(Z[self.std])
            self.ssai = StandardScaler().fit(Z[self.ai])
            A = self.ssai.transform(Z[self.ai])
            self.keep = np.where(Z[self.ai].std(ddof=0).to_numpy() > 0)[0]
            k = min(MAX_PCA, len(X) - 1, len(self.keep))
            self.pca = PCA(n_components=k, svd_solver='full').fit(A[:, self.keep]) if k >= 1 else None
            self.rob, self.rs = [], None
        else:  # 'standard'、または生成AIの変数がないときの 'compressed'
            self.std = list(Z.columns)
            self.ss = StandardScaler().fit(Z[self.std])
            self.rob, self.rs, self.pca = [], None, None
        self.compressed_ai = self.proc == 'compressed' and bool(self.ai)
        return self

    def transform(self, X):
        Z = self._frame(X)
        parts = [self.ss.transform(Z[self.std])]
        if self.rob:
            parts.append(self.rs.transform(Z[self.rob].clip(self.lo, self.hi, axis=1)))
        if self.compressed_ai and self.pca is not None:
            parts.append(self.pca.transform(self.ssai.transform(Z[self.ai])[:, self.keep]))
        return np.hstack(parts)


def inner_splits(tr, endcol):
    """訓練データ tr の中に、時間順の検証分割を最大2つ作る（前処理と罰則の強さを選ぶため）。

    tr を J（jump_day）の順に並べ、最後の約2割を検証ブロックとする（件数は max(MIN_VAL, 件数//5)）。その1つ前の同じ大きさのブロックも検証に使う。
    各検証ブロックの訓練側には、それより前の案件のうち、収益の期間の最終日（endcol の列）が検証ブロックの最初の J より前のもので、
    検証ブロックと同じ会社でないものだけを入れる。これにより、検証の時点でまだ分からない収益で学習することを防ぐ。
    戻り値は（訓練, 検証）の組のリストである。
    """
    t = tr.sort_values(['jump_day', 'code'])
    n = len(t)
    b = max(MIN_VAL, n // 5)
    out = []
    for k in (2, 1):  # 早い検証ブロックを先に、最も新しいブロックを後に作る
        end = n - (k - 1) * b
        start = end - b
        if start <= 0:
            continue
        V = t.iloc[start:end]
        vs = V['jump_day'].min()
        T = t.iloc[:start]
        T = T[(T[endcol] < vs) & (~T['code'].isin(set(V['code'])))]
        if len(T) >= MIN_INNER_TRAIN and len(V) >= MIN_VAL:
            out.append((T, V))
    return out
