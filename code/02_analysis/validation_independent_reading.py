"""Validation of the rule-based extraction against an independent reading of 20 deals (Section 3.5).

For 20 randomly drawn deals, the 11 deal terms were judged again by reading the original
documents without seeing the program's result (data/inputs/独立照合_20件_結果.csv; the
judgment, the evidence sentence, the document and the page are recorded). This program
compares that judgment with the current program judgment (data/processed/deal_terms.csv).

Output  output/tables/validation_independent_reading.csv (one row per deal term)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEAL_TERMS, INPUTS, OUTPUT_TABLES, PROCESSED  # noqa: E402


def main():
    reading = pd.read_csv(INPUTS / "独立照合_20件_結果.csv", dtype={"判定": str})
    terms = pd.read_csv(PROCESSED / "deal_terms.csv", index_col=0)
    column_of = {label: column for column, label in DEAL_TERMS.items()}
    reading["independent_judgment"] = pd.to_numeric(reading["判定"], errors="coerce")   # 「不明」 (not stated) -> missing
    reading["program_judgment"] = [terms.loc[r.案件, column_of[r.変数]] for r in reading.itertuples()]
    compared = reading[reading.independent_judgment.notna() & reading.program_judgment.notna()]

    rows = []
    for label, d in compared.groupby("変数", sort=False):
        rows.append({"deal_term": label, "judgments_compared": len(d),
                     "judgments_agreeing": int((d.independent_judgment == d.program_judgment).sum())})
    rows.append({"deal_term": "合計", "judgments_compared": len(compared),
                 "judgments_agreeing": int((compared.independent_judgment == compared.program_judgment).sum())})
    table = pd.DataFrame(rows)
    table["agreement_rate_pct"] = (100 * table.judgments_agreeing / table.judgments_compared).round(1)
    table.to_csv(OUTPUT_TABLES / "validation_independent_reading.csv", index=False, encoding="utf-8-sig")
    print(f"deals {reading['案件'].nunique()} | judgments {len(reading)} | compared {len(compared)}")
    print(table.to_string(index=False))
    disagree = compared[compared.independent_judgment != compared.program_judgment]
    if len(disagree):
        print(disagree[["案件", "変数", "independent_judgment", "program_judgment", "裁定", "裁定の理由"]].to_string(index=False))


if __name__ == "__main__":
    main()
