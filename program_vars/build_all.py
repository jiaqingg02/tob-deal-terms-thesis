# 11項目の取引条件をプログラム（rules.py の規則）で判定し、生成AIの判定と照合する
#
# 目的：論文の回帰と予測比較で用いる取引条件の変数（部分買付け、入札・競合あり など11項目）を作る。
#       分析に使う変数はすべてここでのプログラム判定であり、生成AIの判定は一致率の確認にだけ用いる。
# 入力：corpus.load() … 生成AIに読ませたものと同一の書類の段落（corpus.py）
#       fulltext.load() … 原文PDFのページごとの本文（fulltext.py）
#       ai_vars_411.csv … 生成AIの判定（照合用）。行は案件で、案件の key は「証券コード_初回公表日」
# 出力：pg_vars_411.csv … 案件×変数の判定（0/1）。01_分析表.py が読む
#       判定の記録.csv     … 案件×変数ごとの判定、該当した規則、根拠文、根拠文のある書類とページ（判定を原文で確かめるための記録）
#       一致率.csv       … 変数ごとの、プログラム判定と生成AIの判定の一致率
# 処理の流れ：①段落と原文を読み込む ②変数ごとに rules.py の関数で判定する ③根拠文が原文のどのページにあるかを探す
#             ④生成AIの判定と照合する
import pandas as pd, corpus, rules, fulltext
B = '../program_vars/'
# 生成AIの判定ファイル（ai_vars_411.csv）の列名は作成時の名前のままなので、読み込み直後に次の日本語名へ改める
AI_COLS = {'AI_部分买付': 'AI_部分買付け',
           'AI_rival_有过竞标或竞争': 'AI_入札競合',
           'A_price_没提价': 'AI_値上げなし',
           'AI_shareholder_没有协议': 'AI_大株主契約なし',
           'AI_regulatory_需要批准或异议': 'AI_許認可待ち',
           'AI_funding_自有资金': 'AI_自己資金'}
VARS = [  # (出力する列名, 判定関数, 照合する生成AIの列, 論文での名称)
    ('PG_部分買付け', rules.partial, 'AI_部分買付け', '部分買付け'),
    ('PG_入札競合', rules.rival, 'AI_入札競合', '入札・競合あり'),
    ('PG_値上げなし', rules.no_raise, 'AI_値上げなし', '交渉で値上げされていない'),
    ('PG_fund', rules.fund, 'buy_fund', '買付者がファンド'),
    ('PG_mbo', rules.mbo, 'buy_mbo', 'MBO'),
    ('PG_大株主契約なし', rules.no_holder_agreement, 'AI_大株主契約なし', '大株主の応募契約なし'),
    ('PG_取締役会中立', rules.board_neutral, 'AI_board_中立', '取締役会が中立'),
    ('PG_許認可待ち', rules.reg_pending, 'AI_許認可待ち', '許認可の承認待ち'),
    ('PG_自己資金', rules.self_funded, 'AI_自己資金', '自己資金'),
    ('PG_優待廃止', rules.perk_abolish, 'IK_優待廃止', '株主優待の廃止'),
    ('PG_親子上場', rules.parent_sub, 'IK_その他類8', '親子上場の解消'),
]
def main():
    """全変数を判定し、判定結果・判定の記録・一致率の3つのファイルを書き出す。"""
    C = corpus.load(); S = pd.read_csv(B + 'ai_vars_411.csv', index_col=0).rename(columns=AI_COLS)   # 生成AIの判定ファイルの列名は作成時の名前のため、読み込み直後に改める
    FT = fulltext.load(S.index)
    for k in S.index: C[k]['_full'] = FT.get(k, [])   # 買付者の種類の判定は原文の全文を読むため、段落と一緒に渡す
    out, trace, agree = pd.DataFrame(index=S.index), [], []
    for name, f, aic, lab in VARS:
        vals = {}
        for k in S.index:
            v, e = f(C[k]); vals[k] = v   # v＝判定（0/1）、e＝根拠文（e.pat は該当した規則）
            # 根拠文が短い（数値条件だけで判定した場合など）と原文の位置を特定できないため、13字以上のときだけ探す
            kind, doc, page = fulltext.locate(FT, k, e, fulltext.anchor_of(e, getattr(e, 'pat', ''))) if isinstance(e, str) and len(e) > 12 else ('', '', '')
            trace.append({'案件': k, '変数': lab, 'プログラム判定': v, 'AI判定': S.loc[k, aic] if aic in S else '', '規則': getattr(e, 'pat', '') or ('数値条件' if e else ''),
                          '根拠文': e, '資料': kind, '文書ID': doc, 'ページ': page})
        out[name] = pd.Series(vals)
        a = S[aic]; ok = a.notna() & out[name].notna(); p, q = out[name][ok].astype(int), a[ok].astype(int)   # 原文に記載がない（欠測の）案件は照合から除く
        agree.append({'変数': lab, '件数': int(ok.sum()), '一致率': round((p == q).mean() * 100, 1), 'AI=1': int(q.sum()), 'プログラム=1': int(p.sum()), '両方1': int((p & q).sum())})
    out.to_csv(B + 'pg_vars_411.csv', encoding='utf-8-sig')
    pd.DataFrame(trace).to_csv(B + '判定の記録.csv', index=False, encoding='utf-8-sig')
    A = pd.DataFrame(agree); A.to_csv(B + '一致率.csv', index=False, encoding='utf-8-sig'); print(A.to_string(index=False))
if __name__ == '__main__': main()
