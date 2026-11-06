# 予測モデルの前処理と時系列の分割。出典：Codex 実験コード work/processing_experiment/run.py の Prep・inner_splits・OUTER などを一字も変えずに写したもの（論文フォルダだけで再現できるようにするため）
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
    def __init__(self, num, ai, proc, cont):
        self.num, self.ai, self.proc, self.cont = list(num), list(ai), proc, set(cont)

    def _frame(self, X):
        Z = X[self.num + self.ai].astype(float).copy()
        for c in self.miss:
            Z[c + '__miss'] = X[c].isna().astype(float)
        return Z.fillna(self.med)

    def fit(self, X):
        base = X[self.num + self.ai].astype(float)
        self.miss = [c for c in self.num + self.ai if base[c].isna().any()]
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
        else:  # standard，或无AI块时的 compressed
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
    t = tr.sort_values(['jump_day', 'code'])
    n = len(t)
    b = max(MIN_VAL, n // 5)
    out = []
    for k in (2, 1):  # 较早的验证块在前，最近的在后
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
