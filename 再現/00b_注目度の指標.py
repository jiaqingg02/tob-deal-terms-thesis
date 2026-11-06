# 注目度の指標を、保存済みの株探ニュース標題・日経の検索結果・株価から計算する（04_注目度.py が読む）
#   入力：株探のニュース標題（data/news・data_old/news の kabutan_YYYYMM.csv）、社名と別名（tob_deals.csv・news_alias.csv）、
#         日経電子版の検索結果（attention/nikkei_gnews.csv：Google ニュースで「site:nikkei.com 社名＋TOB 関連語」を検索し、標題に社名がある記事を保存したもの。
#         検索は attention/nikkei_gnews.py で1回だけ行った。検索結果は時間とともに変わるので、ここでは保存した標題から数え直す）、株価（終値・出来高）
#   出力：中間/注目度の指標.csv、中間/注目度の指標_照合.csv（以前の版 attention/sample_with_attention2.csv との照合）
#
#   計算式（a＝公表日、標本＝回帰に使う411件）
#     株探の記事数   K前＝[a−30日, a) の標題数、K後＝[a, a+8日) の標題数（社名・略称・別名を含む標題）
#     株探の事前報道 L株探＝1（[a−90日, a) の社名を含む標題に「報道」「観測」「伝わ」「最有力」がある）
#     日経の報道     N前・N後＝保存した日経の標題のうち、TOB 関連語（TOB・買収・公開買い付け・非公開化・完全子会社・子会社化・経営統合・MBO など）を含むものの数
#                    （公表日15時より前＝事前、その後〜7日＝事後。略称が一般語の会社は正式社名も必要。別の会社・別の取引の記事2件は除く）
#     事前報道       L＝1（L株探＝1 または N前＞0）
#     平常の売買代金 V＝中央値（終値×出来高）、公表日（またはその前の最後の営業日）を j として j−65〜j−6 営業日（30日以上あるとき）、単位は億円。log V＝ln(V＋0.001)
#     合成注目度     A＝［R(log V)＋R(K前)＋R(K後)］÷3、R＝411件の中での百分位順位（0〜1、同順位は平均順位）
import csv, glob, bisect, unicodedata, re, numpy as np, pandas as pd
from datetime import date, timedelta
from pathlib import Path
B = Path('..'); H = B / '再現'
R = pd.read_csv(H / '中間/収益と価格差.csv', index_col=0)
KEYS = R.index[R.spread_J1.notna()]   # 回帰に使う411件

def norm(s):
    s = unicodedata.normalize('NFKC', s)
    for c in '・−- 　': s = s.replace(c, '')
    return s.upper()
def variants(name):   # 社名の表記ゆれ（ホールディングス↔HD、グループを除いた名前）
    n = norm(name); v = {n}
    for suf in ['ホールディングス', 'ホールディング', 'グループ']:
        if n.endswith(norm(suf)):
            core = n[:-len(norm(suf))]
            if len(core) >= 2: v |= {core + 'HD', core}
    if n.endswith('HD') and len(n) >= 4: v.add(n[:-2] + 'ホールディングス')
    v = {x.replace('株式会社', '') for x in v}
    return {x for x in v if len(x) >= 2}
alias = {}
for f in [B / 'data/news_alias.csv', B / 'data_old/news_alias_old.csv']:
    for r in csv.DictReader(open(f, encoding='utf-8-sig')):
        a = r.get('alias') or list(r.values())[1]
        if a: alias.setdefault(r['code'], set()).add(norm(a))
news = []
for f in sorted(set(glob.glob(str(B / 'data/news/kabutan_*.csv')) + glob.glob(str(B / 'data_old/news/kabutan_*.csv'))), key=lambda p: Path(p).name):
    for r in csv.reader(open(f, encoding='utf-8-sig')):
        if r and r[0] != 'date': news.append((r[0], r[2], norm(r[2])))
news = sorted(set(news)); dates = [n[0] for n in news]
names = {}
for f in [B / 'data/tob_deals.csv', B / 'data_old/tob_deals.csv']:
    for r in csv.DictReader(open(f, encoding='utf-8-sig')):
        if r['target_name']: names[(r['target_code'], r['first_date'])] = r['target_name']
LEAK = re.compile('報道|観測|伝わ|最有力')
rows = []
for k in KEYS:
    code, ann = k.split('_'); name = names.get((code, ann)); r = {'key': k, 'name': name}
    vs = variants(name) | alias.get(code, set())
    def hits(lo, hi):
        i0, i1 = bisect.bisect_left(dates, lo), bisect.bisect_left(dates, hi)
        return [n for n in news[i0:i1] if any(v in n[2] for v in vs)]
    a = date.fromisoformat(ann)
    pre90 = hits((a - timedelta(days=90)).isoformat(), ann)
    r.update(事前报道数=len(hits((a - timedelta(days=30)).isoformat(), ann)), 事后报道数=len(hits(ann, (a + timedelta(days=8)).isoformat())),
             事前收购报道=int(any(LEAK.search(n[1]) for n in pre90)))
    p = pd.read_csv(B / ('data' if ann >= '2022' else 'data_old') / 'prices' / f'{k}.csv'); p = p[p.volume.notna()].reset_index(drop=True)
    j = p.index[p.date <= ann][-1]
    base = p.iloc[max(j - 65, 0): max(j - 5, 0)]
    r['平常売買代金_亿'] = float((base.close * base.volume).median() / 1e8) if len(base) >= 30 and base.volume.mean() > 0 else np.nan
    rows.append(r)
S = pd.DataFrame(rows).set_index('key')
# 日経の報道（保存した検索結果の標題を TOB 関連語で絞る）
KW = re.compile('TOB|買収|公開買い付け|公開買付|非公開化|完全子会社|子会社化|一部報道|経営統合|買い付け|MBO')
GENERIC = {'デジタル', 'トラスト'}   # 略称が一般語の会社は正式社名も標題に必要
N = pd.read_csv(B / 'attention/nikkei_gnews.csv').fillna('').set_index('key').reindex(KEYS).fillna('')
def nm(s): return unicodedata.normalize('NFKC', s).replace(' ', '').upper()
def keep(t, k):
    if not KW.search(t): return False
    if N.loc[k, 'query_name'] in GENERIC: return nm(S.loc[k, 'name']).replace('株式会社', '') in nm(t)
    return True
for col, out in [('事前标题', '日经_事前'), ('事后标题', '日经_事后')]:
    S[out] = [sum(1 for t in str(N.loc[k, col]).split(' ｜ ') if t and keep(t, k)) for k in KEYS]
S.loc[['9719_2025-10-29', '6271_2021-11-08'], '日经_事前'] = 0   # 人手で確認：事前の標題が別の会社・別の取引（SCSK＝ネットワンとの統合、ニッセイ＝日本生命グループの別会社）
S['抢先报道_任一'] = ((S.事前收购报道 == 1) | (S.日经_事前 > 0)).astype(int)
S['log売買代金'] = np.log(S.平常売買代金_亿 + 1e-3)
S['关注度'] = S[['log売買代金', '事前报道数', '事后报道数']].rank(pct=True).mean(axis=1)
S.to_csv(H / '中間/注目度の指標.csv', encoding='utf-8-sig')

# 以前の版（attention/build_attention.py → analyze.py → nikkei_filter.py → analyze2.py）と照合
T = pd.read_csv(B / 'attention/sample_with_attention2.csv', index_col=0).reindex(KEYS)
cmp = [{'項目': c, '一致件数': int((((S[c] - T[c]).abs() < 1e-9) | (S[c].isna() & T[c].isna())).sum()), '件数': len(KEYS)}
       for c in ['事前报道数', '事后报道数', '事前收购报道', '平常売買代金_亿', 'log売買代金', '日经_事前', '日经_事后', '抢先报道_任一', '关注度']]
pd.DataFrame(cmp).to_csv(H / '中間/注目度の指標_照合.csv', index=False, encoding='utf-8-sig')
print('注目度の指標', len(S), '件'); print(pd.DataFrame(cmp).to_string(index=False))
