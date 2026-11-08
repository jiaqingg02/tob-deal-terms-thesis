"""Appendix A: agreement between the rule-based deal terms and the earlier judgments by a generative AI,
for the 403 deals in the analysis sample.

The earlier AI judgments were made before the rules were written (data/processed/earlier_ai_judgments.csv,
saved by code/01_dataprep/04_extract_deal_terms.py). Every judgment where the two disagreed was checked
against the original documents (data/inputs/document_check_of_disagreements_with_ai.csv: the correct value,
the reason, the sentence, the document and the page). This program counts, for each term, how many
judgments agree, and for the judgments that disagree, whether the final rule-based value equals the value
confirmed in the original documents.

For 親子上場の解消, the earlier AI label was a broader category made by the AI itself
(「親子上場の解消など」), so its definition is not the same as that of the rule. It is reported but marked.

Output  output/tables/appendix_a_agreement_with_ai.csv (one row per deal term, and a total row)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEAL_TERMS, INPUTS, OUTPUT_TABLES, PROCESSED  # noqa: E402
from sample import load_sample  # noqa: E402

TERMS_WITH_DIFFERENT_AI_DEFINITION = {"term_resolves_parent_subsidiary_listing"}


def main():
    sample = load_sample()
    rules = pd.read_csv(PROCESSED / "deal_terms.csv", index_col=0).loc[sample.index]
    ai = pd.read_csv(PROCESSED / "earlier_ai_judgments.csv", index_col=0).reindex(sample.index)
    checked = pd.read_csv(INPUTS / "document_check_of_disagreements_with_ai.csv")
    checked = checked.drop_duplicates(["deal_id", "deal_term"], keep="last").set_index(["deal_id", "deal_term"])["correct_value"]

    rows = []
    for column, name in DEAL_TERMS.items():
        r, a = rules[column], ai["ai_" + column.removeprefix("term_")]
        ok = r.notna() & a.notna()   # deals where either side has no value (no funding statement) are not compared
        r, a = r[ok].astype(int), a[ok].astype(int)
        differ = r.index[r != a]
        confirmed = sum(int(checked.get((k, name), -1)) == r[k] for k in differ)
        rows.append({"deal_term": name,
                     "ai_definition_same_as_rule": column not in TERMS_WITH_DIFFERENT_AI_DEFINITION,
                     "judgments_compared": int(ok.sum()),
                     "judgments_agreeing": int((r == a).sum()),
                     "agreement_rate_pct": round((r == a).mean() * 100, 1),
                     "judgments_disagreeing": len(differ),
                     "disagreements_where_rule_equals_original_document": confirmed,
                     "disagreements_not_resolved_in_favour_of_rule": len(differ) - confirmed})
    table = pd.DataFrame(rows)
    same = table[table.ai_definition_same_as_rule]
    total = {"deal_term": "合計（AIの定義が同じ10項目）", "ai_definition_same_as_rule": True}
    for c in ["judgments_compared", "judgments_agreeing", "judgments_disagreeing",
              "disagreements_where_rule_equals_original_document", "disagreements_not_resolved_in_favour_of_rule"]:
        total[c] = int(same[c].sum())
    total["agreement_rate_pct"] = round(total["judgments_agreeing"] / total["judgments_compared"] * 100, 1)
    table = pd.concat([table, pd.DataFrame([total])], ignore_index=True)
    table.to_csv(OUTPUT_TABLES / "appendix_a_agreement_with_ai.csv", index=False, encoding="utf-8-sig")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
