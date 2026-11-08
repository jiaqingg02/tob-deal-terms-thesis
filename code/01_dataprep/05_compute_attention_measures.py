"""Compute the measures of market attention used in Section 5 (attention).

  kabutan_articles_30_days_before        Kabutan headlines naming the target in the 30 days before the announcement
  kabutan_articles_7_days_after          the same from the announcement day to 7 days after
  kabutan_takeover_report_90_days_before 1 if a headline in the 90 days before reports the takeover (報道・観測・伝わ・最有力)
  normal_trading_value_100m_yen          median daily trading value (100 million yen) over trading days j-65..j-6
  log_normal_trading_value               log of the above
  nikkei_articles_before / _after        Nikkei headlines (Google News search) about the takeover before / after
  reported_before_announcement           1 if the takeover was reported by Kabutan or Nikkei before the announcement
  composite_attention_score              mean percentile rank of log trading value and the two Kabutan counts

Inputs
  data/processed/price_gap.csv
  RAW_DATA/data*/news/kabutan_*.csv, news_alias*.csv, tob_deals.csv, prices/
  RAW_DATA/attention/nikkei_gnews.csv, attention/sample_with_attention2.csv (earlier file, comparison only)
Output
  data/processed/attention_measures.csv
"""
import csv, glob, bisect, unicodedata, re, numpy as np, pandas as pd
from datetime import date, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_TABLES, PROCESSED, RAW_DATA  # noqa: E402
B = RAW_DATA
R = pd.read_csv(PROCESSED / 'price_gap.csv', index_col=0)
KEYS = R.index[R.price_gap_at_start_ratio.notna()]   # deals with a price gap

def norm(s):
    """照合用に社名・標題を正規化する（NFKC、中黒・ハイフン・空白を除き、英字を大文字にする）。"""
    s = unicodedata.normalize('NFKC', s)
    for c in '・−- 　': s = s.replace(c, '')
    return s.upper()
def variants(name):   # 社名の表記ゆれの集合（ホールディングス↔HD、ホールディングス・グループを除いた名前、「株式会社」を除いた名前）
    n = norm(name); v = {n}
    for suf in ['ホールディングス', 'ホールディング', 'グループ']:
        if n.endswith(norm(suf)):
            core = n[:-len(norm(suf))]
            if len(core) >= 2: v |= {core + 'HD', core}
    if n.endswith('HD') and len(n) >= 4: v.add(n[:-2] + 'ホールディングス')
    v = {x.replace('株式会社', '') for x in v}
    return {x for x in v if len(x) >= 2}
alias = {}
for f in [B / 'data/news_alias.csv', B / 'data_old/news_alias_old.csv']:   # 証券コード → 株探で使われる略称・別名
    for r in csv.DictReader(open(f, encoding='utf-8-sig')):
        a = r.get('alias') or list(r.values())[1]
        if a: alias.setdefault(r['code'], set()).add(norm(a))
news = []
for f in sorted(set(glob.glob(str(B / 'data/news/kabutan_*.csv')) + glob.glob(str(B / 'data_old/news/kabutan_*.csv'))), key=lambda p: Path(p).name):
    for r in csv.reader(open(f, encoding='utf-8-sig')):
        if r and r[0] != 'date': news.append((r[0], r[2], norm(r[2])))
news = sorted(set(news)); dates = [n[0] for n in news]   # (日付, 標題, 正規化した標題)。重複を除き日付順に並べ、期間の検索に二分探索を使う
names = {}
for f in [B / 'data/tob_deals.csv', B / 'data_old/tob_deals.csv']:
    for r in csv.DictReader(open(f, encoding='utf-8-sig')):
        if r['target_name']: names[(r['target_code'], r['first_date'])] = r['target_name']
LEAK = re.compile('報道|観測|伝わ|最有力')   # 株探の標題で、公表前の報道を示す語
rows = []
for k in KEYS:
    code, ann = k.split('_'); name = names.get((code, ann)); r = {'deal_id': k, 'target_company_name': name}
    vs = variants(name) | alias.get(code, set())
    def hits(lo, hi):   # 日付が [lo, hi) で、社名の表記のどれかを含む株探の標題
        i0, i1 = bisect.bisect_left(dates, lo), bisect.bisect_left(dates, hi)
        return [n for n in news[i0:i1] if any(v in n[2] for v in vs)]
    a = date.fromisoformat(ann)
    pre90 = hits((a - timedelta(days=90)).isoformat(), ann)
    r.update(kabutan_articles_30_days_before=len(hits((a - timedelta(days=30)).isoformat(), ann)), kabutan_articles_7_days_after=len(hits(ann, (a + timedelta(days=8)).isoformat())),
             kabutan_takeover_report_90_days_before=int(any(LEAK.search(n[1]) for n in pre90)))
    p = pd.read_csv(B / ('data' if ann >= '2022' else 'data_old') / 'prices' / f'{k}.csv'); p = p[p.volume.notna()].reset_index(drop=True)
    j = p.index[p.date <= ann][-1]
    base = p.iloc[max(j - 65, 0): max(j - 5, 0)]   # j−65〜j−6 取引日（公表直前の5取引日は含めない）
    r['normal_trading_value_100m_yen'] = float((base.close * base.volume).median() / 1e8) if len(base) >= 30 and base.volume.mean() > 0 else np.nan
    rows.append(r)
S = pd.DataFrame(rows).set_index('deal_id')
KW = re.compile('TOB|買収|公開買い付け|公開買付|非公開化|完全子会社|子会社化|一部報道|経営統合|買い付け|MBO')
GENERIC = {'デジタル', 'トラスト'}   # 略称が一般語の会社は正式社名も標題に必要
N = pd.read_csv(B / 'attention/nikkei_gnews.csv').rename(columns={'事前标题': '事前見出し', '事后标题': '事後見出し'}).fillna('').set_index('key').reindex(KEYS).fillna('')
def nm(s): return unicodedata.normalize('NFKC', s).replace(' ', '').upper()   # 日経の標題の照合用の正規化（NFKC、空白を除き英字を大文字にする）
def keep(t, k):
    """日経の標題 t を案件 k の報道として数えるか。TOB 関連語を含み、略称が一般語の会社では正式社名も含むものだけを数える。"""
    if not KW.search(t): return False
    if N.loc[k, 'query_name'] in GENERIC: return nm(S.loc[k, 'target_company_name']).replace('株式会社', '') in nm(t)
    return True
for col, out in [('事前見出し', 'nikkei_articles_before'), ('事後見出し', 'nikkei_articles_after')]:
    S[out] = [sum(1 for t in str(N.loc[k, col]).split(' ｜ ') if t and keep(t, k)) for k in KEYS]
S.loc[['9719_2025-10-29', '6271_2021-11-08'], 'nikkei_articles_before'] = 0   # 人手で確認：事前の標題が別の会社・別の取引（SCSK＝ネットワンとの統合、ニッセイ＝日本生命グループの別会社）
S['reported_before_announcement'] = ((S.kabutan_takeover_report_90_days_before == 1) | (S.nikkei_articles_before > 0)).astype(int)
S['log_normal_trading_value'] = np.log(S.normal_trading_value_100m_yen + 1e-3)
S['composite_attention_score'] = S[['log_normal_trading_value', 'kabutan_articles_30_days_before', 'kabutan_articles_7_days_after']].rank(pct=True).mean(axis=1)
S.to_csv(PROCESSED / 'attention_measures.csv', encoding='utf-8-sig')

OLD_COLS = {'事前报道数': 'kabutan_articles_30_days_before', '事后报道数': 'kabutan_articles_7_days_after', '事前收购报道': 'kabutan_takeover_report_90_days_before', '平常売買代金_亿': 'normal_trading_value_100m_yen', 'log売買代金': 'log_normal_trading_value', '日经_事前': 'nikkei_articles_before', '日经_事后': 'nikkei_articles_after', '抢先报道_任一': 'reported_before_announcement', '关注度': 'composite_attention_score'}   # earlier file (comparison only)
T = pd.read_csv(B / 'attention/sample_with_attention2.csv', index_col=0).rename(columns=OLD_COLS).reindex(KEYS)
cmp = [{'variable': c, 'number_equal_to_earlier_file': int((((S[c] - T[c]).abs() < 1e-9) | (S[c].isna() & T[c].isna())).sum()), 'number_of_deals': len(KEYS)}
       for c in OLD_COLS.values()]
pd.DataFrame(cmp).to_csv(PROCESSED / 'attention_measures_comparison_with_earlier_file.csv', index=False, encoding='utf-8-sig')
print('attention measures', len(S), 'deals'); print(pd.DataFrame(cmp).to_string(index=False))
