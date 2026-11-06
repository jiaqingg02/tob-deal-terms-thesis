# 全变量の程序判定 → ①pg_vars_411.csv（回帰用） ②判定留痕.csv（件×変数ごとの依据句・規則・原文ページ） ③一致率.csv
import pandas as pd, corpus, rules, fulltext
B = '../program_vars/'
VARS = [  # (プログラムの変数名, 判定関数, 照合する生成AIの列, 論文での名称)
    ('PG_部分买付', rules.partial, 'AI_部分买付', '部分買付け'),
    ('PG_入札競合', rules.rival, 'AI_rival_有过竞标或竞争', '入札・競合あり'),
    ('PG_没提价', rules.no_raise, 'A_price_没提价', '交渉で値上げされていない'),
    ('PG_fund', rules.fund, 'buy_fund', '買付者がファンド'),
    ('PG_mbo', rules.mbo, 'buy_mbo', 'MBO'),
    ('PG_大株主契約なし', rules.no_holder_agreement, 'AI_shareholder_没有协议', '大株主の応募契約なし'),
    ('PG_取締役会中立', rules.board_neutral, 'AI_board_中立', '取締役会が中立'),
    ('PG_許認可待ち', rules.reg_pending, 'AI_regulatory_需要批准或异议', '許認可の承認待ち'),
    ('PG_自己資金', rules.self_funded, 'AI_funding_自有资金', '自己資金'),
    ('PG_優待廃止', rules.perk_abolish, 'IK_優待廃止', '株主優待の廃止'),
    ('PG_親子上場', rules.parent_sub, 'IK_その他類8', '親子上場の解消'),
]
def main():
    C = corpus.load(); S = pd.read_csv(B + 'ai_vars_411.csv', index_col=0)
    FT = fulltext.load(S.index)
    for k in S.index: C[k]['_full'] = FT.get(k, [])
    out, trace, agree = pd.DataFrame(index=S.index), [], []
    for name, f, aic, lab in VARS:
        vals = {}
        for k in S.index:
            v, e = f(C[k]); vals[k] = v
            kind, doc, page = fulltext.locate(FT, k, e, fulltext.anchor_of(e, getattr(e, 'pat', ''))) if isinstance(e, str) and len(e) > 12 else ('', '', '')
            trace.append({'案件': k, '変数': lab, '程序判定': v, 'AI判定': S.loc[k, aic] if aic in S else '', '規則': getattr(e, 'pat', '') or ('数値条件' if e else ''),
                          '依据句': e, '資料': kind, '文書ID': doc, 'ページ': page})
        out[name] = pd.Series(vals)
        a = S[aic]; ok = a.notna() & out[name].notna(); p, q = out[name][ok].astype(int), a[ok].astype(int)   # 原文に記載がない（欠測）ものは照合から除く
        agree.append({'変数': lab, '件数': int(ok.sum()), '一致率': round((p == q).mean() * 100, 1), 'AI=1': int(q.sum()), '程序=1': int(p.sum()), '両方1': int((p & q).sum())})
    out.to_csv(B + 'pg_vars_411.csv', encoding='utf-8-sig')
    pd.DataFrame(trace).to_csv(B + '判定留痕.csv', index=False, encoding='utf-8-sig')
    A = pd.DataFrame(agree); A.to_csv(B + '一致率.csv', index=False, encoding='utf-8-sig'); print(A.to_string(index=False))
if __name__ == '__main__': main()
