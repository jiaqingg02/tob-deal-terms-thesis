"""Extract the 11 deal terms from the disclosure documents with fixed rules (Section 3.4)
and compare the result with the earlier judgments made by a generative AI (Section 3.5).

The rules are in deal_term_rules.py (keywords and numeric conditions written by
hand; no generative AI is used). The input paragraphs are those cut from the
registration statement and the opinion statement (document_paragraphs.py); the
acquirer type (fund / MBO) is judged from the full text (document_full_text.py).

Inputs
  RAW_DATA/fill_summary/   paragraphs cut from the documents
  RAW_DATA/program_vars/ai_vars_411.csv   earlier judgments by a generative AI (comparison only)
  original PDFs (see document_full_text.py)
Outputs
  data/processed/deal_terms.csv                 one row per deal, one 0/1 column per term
  data/processed/deal_term_evidence.csv         evidence sentence, rule, document and page for each judgment
  output/tables/deal_terms_agreement_with_ai.csv  agreement rate with the earlier AI judgments
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deal_term_rules as rules  # noqa: E402
import document_full_text  # noqa: E402
import document_paragraphs  # noqa: E402
from config import DEAL_TERMS, OUTPUT_TABLES, PROCESSED, RAW_DATA  # noqa: E402

# column names of the earlier AI judgment file -> names used here
AI_COLUMNS = {"AI_部分买付": "ai_partial_tender_offer",
              "AI_rival_有过竞标或竞争": "ai_competitive_bidding",
              "A_price_没提价": "ai_no_price_increase_in_negotiation",
              "AI_shareholder_没有协议": "ai_no_tender_agreement_with_major_shareholder",
              "AI_regulatory_需要批准或异议": "ai_pending_regulatory_approval",
              "AI_funding_自有资金": "ai_financed_by_own_funds",
              "AI_board_中立": "ai_board_opinion_is_neutral",
              "buy_fund": "ai_acquirer_is_investment_fund",
              "buy_mbo": "ai_management_buyout",
              "IK_優待廃止": "ai_abolishes_shareholder_benefits",
              "IK_その他類8": "ai_resolves_parent_subsidiary_listing"}

TERMS = [  # (column name, rule)
    ("term_partial_tender_offer", rules.partial),
    ("term_competitive_bidding", rules.rival),
    ("term_no_price_increase_in_negotiation", rules.no_raise),
    ("term_acquirer_is_investment_fund", rules.fund),
    ("term_management_buyout", rules.mbo),
    ("term_no_tender_agreement_with_major_shareholder", rules.no_holder_agreement),
    ("term_board_opinion_is_neutral", rules.board_neutral),
    ("term_pending_regulatory_approval", rules.reg_pending),
    ("term_financed_by_own_funds", rules.self_funded),
    ("term_abolishes_shareholder_benefits", rules.perk_abolish),
    ("term_resolves_parent_subsidiary_listing", rules.parent_sub),
]


def judge(deal_ids, paragraphs, full_text):
    """Apply every rule to every deal. Returns (0/1 table, evidence records)."""
    table, evidence = pd.DataFrame(index=pd.Index(deal_ids, name="deal_id")), []
    for name, rule in TERMS:
        values = {}
        for k in deal_ids:
            value, sentence = rule(paragraphs[k])
            values[k] = value
            # the page is searched only for evidence of 13+ characters (short evidence cannot be located)
            if isinstance(sentence, str) and len(sentence) > 12:
                kind, doc, page = document_full_text.locate(
                    full_text, k, sentence, document_full_text.anchor_of(sentence, getattr(sentence, "pat", "")))
            else:
                kind, doc, page = "", "", ""
            evidence.append({"deal_id": k, "deal_term": DEAL_TERMS[name], "judgment": value,
                             "matched_rule": getattr(sentence, "pat", "") or ("数値条件" if sentence else ""),
                             "evidence_sentence": sentence, "document_type": kind, "document_id": doc, "page": page})
        table[name] = pd.Series(values)
    return table, evidence


def main():
    paragraphs = document_paragraphs.load()
    ai = pd.read_csv(RAW_DATA / "program_vars" / "ai_vars_411.csv", index_col=0).rename(columns=AI_COLUMNS)
    deal_ids = list(ai.index)
    # the 2 deals without a price gap are not in the AI file; they are judged with the same rules
    deal_ids += [k for k in pd.read_csv(PROCESSED / "price_gap.csv", index_col=0).index if k not in ai.index]
    full_text = document_full_text.load(deal_ids)
    for k in deal_ids:
        paragraphs[k]["_full"] = full_text.get(k, [])   # the acquirer-type rules read the full text
    table, evidence = judge(deal_ids, paragraphs, full_text)
    table.to_csv(PROCESSED / "deal_terms.csv", encoding="utf-8-sig")
    pd.DataFrame(evidence).to_csv(PROCESSED / "deal_term_evidence.csv", index=False, encoding="utf-8-sig")

    agreement = []
    for name, _ in TERMS:
        ai_col = "ai_" + name.removeprefix("term_")
        a = ai[ai_col]
        p = table.loc[ai.index, name]
        ok = a.notna() & p.notna()   # deals where the document says nothing are excluded
        p, q = p[ok].astype(int), a[ok].astype(int)
        agreement.append({"deal_term": DEAL_TERMS[name], "number_of_deals": int(ok.sum()),
                          "agreement_rate_pct": round((p == q).mean() * 100, 1),
                          "deals_judged_1_by_ai": int(q.sum()), "deals_judged_1_by_rules": int(p.sum()),
                          "deals_judged_1_by_both": int((p & q).sum())})
    agreement = pd.DataFrame(agreement)
    agreement.to_csv(OUTPUT_TABLES / "deal_terms_agreement_with_ai.csv", index=False, encoding="utf-8-sig")
    print(agreement.to_string(index=False))


if __name__ == "__main__":
    main()
