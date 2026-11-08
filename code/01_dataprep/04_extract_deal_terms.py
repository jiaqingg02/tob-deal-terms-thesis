"""Extract the 11 deal terms from the disclosure documents with fixed rules (Section 3.4)
and save the earlier judgments made by a generative AI for comparison (Appendix A).

The rules are in deal_term_rules.py (keywords and numeric conditions written by
hand; no generative AI is used). The input paragraphs are those cut from the
registration statement and the opinion statement (document_paragraphs.py); the
acquirer type (fund / MBO) is judged from the full text (document_full_text.py).

Inputs
  RAW_DATA/fill_summary/   paragraphs cut from the documents
  RAW_DATA/program_vars/ai_vars_411.csv   earlier judgments by a generative AI (comparison only)
  original PDFs (see document_full_text.py)
  corrections_after_document_check.csv   values corrected after checking the original documents
Outputs
  data/processed/deal_terms.csv                 one row per deal, one 0/1 column per term
  data/processed/deal_term_evidence.csv         evidence sentence, rule, document and page for each judgment
  data/processed/earlier_ai_judgments.csv       earlier AI judgments, renamed to the same terms (comparison only)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deal_term_rules as rules  # noqa: E402
import document_full_text  # noqa: E402
import document_paragraphs  # noqa: E402
from config import DEAL_TERMS, PROCESSED, RAW_DATA  # noqa: E402

# column names of the earlier AI judgment file -> names used here
AI_COLUMNS = {"AI_部分买付": "ai_partial_tender_offer",
              "AI_rival_有过竞标或竞争": "ai_competitive_bidding",
              "A_price_没提价": "ai_no_price_increase_confirmed_in_negotiation_with_target",
              "AI_shareholder_没有协议": "ai_no_tender_or_non_tender_agreement_with_shareholders",
              "AI_regulatory_需要批准或异议": "ai_pending_regulatory_approval",
              "AI_funding_自有资金": "ai_no_borrowing_or_equity_financing_planned",
              "AI_board_中立": "ai_board_does_not_recommend_tender",
              "buy_fund": "ai_investment_fund_involved_in_acquirer",
              "buy_mbo": "ai_management_buyout_without_fund",
              "IK_優待廃止": "ai_abolishes_shareholder_benefits",
              "IK_その他類8": "ai_resolves_parent_subsidiary_listing"}

TERMS = [  # (column name, rule)
    ("term_partial_tender_offer", rules.partial),
    ("term_competitive_bidding", rules.rival),
    ("term_no_price_increase_confirmed_in_negotiation_with_target", rules.no_raise),
    ("term_investment_fund_involved_in_acquirer", rules.fund),
    ("term_management_buyout_without_fund", rules.mbo),
    ("term_no_tender_or_non_tender_agreement_with_shareholders", rules.no_holder_agreement),
    ("term_board_does_not_recommend_tender", rules.board_neutral),
    ("term_pending_regulatory_approval", rules.reg_pending),
    ("term_no_borrowing_or_equity_financing_planned", rules.self_funded),
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
    # Corrections found by checking the original documents (corrections_after_document_check.csv).
    # Each row gives the deal, the term, the value given by the rules, the corrected value, the reason and
    # the sentence, document and page that show the correct value. The rule value is checked first so that
    # a correction is never applied to a value the rules no longer produce.
    corrections = pd.read_csv(Path(__file__).resolve().parent / "corrections_after_document_check.csv")
    for r in corrections.itertuples():
        assert table.at[r.deal_id, r.deal_term_column] == r.rule_value, (r.deal_id, r.deal_term_column)
        table.at[r.deal_id, r.deal_term_column] = r.corrected_value
        for e in evidence:
            if e["deal_id"] == r.deal_id and e["deal_term"] == DEAL_TERMS[r.deal_term_column]:
                e.update(judgment=r.corrected_value, matched_rule="原文確認による修正：" + r.reason,
                         evidence_sentence=r.evidence_sentence, document_type="", document_id=r.document_id, page=r.page)
    table.to_csv(PROCESSED / "deal_terms.csv", encoding="utf-8-sig")
    pd.DataFrame(evidence).to_csv(PROCESSED / "deal_term_evidence.csv", index=False, encoding="utf-8-sig")

    # the earlier AI judgments are saved for the comparison in Appendix A (code/02_analysis/appendix_a_agreement_with_ai.py)
    ai[list(AI_COLUMNS.values())].to_csv(PROCESSED / "earlier_ai_judgments.csv", encoding="utf-8-sig")


if __name__ == "__main__":
    main()
