"""Export the data made in this study that can be published with the code (data/published/).

Stock prices and the indices computed from them (price gap, premium, returns) are not exported,
because the price data cannot be redistributed. The original documents can be obtained from EDINET.

Outputs (data/published/)
  deal_list.csv                                  deals whose documents were read (413), document IDs, filing times,
                                                 and whether the deal is in the analysis sample (403)
  deal_terms.csv                                 the 11 deal terms (1 / 0, missing for funding without a statement)
  deal_term_evidence.csv                         for each deal and term: the rule that matched, the evidence sentence,
                                                 the document and the page
  earlier_ai_judgments.csv                       judgments made earlier by a generative AI (used only in Appendix A)
  document_check_of_disagreements_with_ai.csv    the value confirmed in the original documents for each disagreement
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INPUTS, PROCESSED, PUBLISHED  # noqa: E402

DEAL_LIST_COLUMNS = [
    "deal_id", "target_securities_code", "announcement_date", "return_start_date",
    "registration_statement_document_id", "opinion_statement_document_id",
    "registration_statement_filed_at", "opinion_statement_filed_at",
    "document_availability_at_return_start", "excluded_by_filing_rule", "in_analysis_sample",
]


def main():
    table = pd.read_csv(PROCESSED / "analysis_table.csv", dtype={"target_securities_code": str})
    table[DEAL_LIST_COLUMNS].to_csv(PUBLISHED / "deal_list.csv", index=False, encoding="utf-8-sig")
    for name in ["deal_terms.csv", "deal_term_evidence.csv", "earlier_ai_judgments.csv"]:
        shutil.copyfile(PROCESSED / name, PUBLISHED / name)
    shutil.copyfile(INPUTS / "document_check_of_disagreements_with_ai.csv",
                    PUBLISHED / "document_check_of_disagreements_with_ai.csv")
    for f in sorted(PUBLISHED.glob("*.csv")):
        print(f.name, len(pd.read_csv(f)), "rows")


if __name__ == "__main__":
    main()
