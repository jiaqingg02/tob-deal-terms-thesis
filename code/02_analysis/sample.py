"""Load the analysis sample (403 deals, Section 3.2) and check its size.

The program stops if the numbers of deals differ from those in the paper
(config.EXPECTED_SAMPLE_SIZE): all deals, partial offers (term_partial_tender_offer = 1)
and deals pinned to the offer price (|price gap at start| <= config.PINNED_THRESHOLD_PCT,
partial offers included).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EXPECTED_SAMPLE_SIZE, PINNED_THRESHOLD_PCT, PROCESSED  # noqa: E402


def load_analysis_table() -> pd.DataFrame:
    """All 413 deals whose documents were read (see code/01_dataprep/06_build_analysis_table.py)."""
    return pd.read_csv(PROCESSED / "analysis_table.csv", index_col=0,
                       dtype={"target_securities_code": str}, keep_default_na=False,
                       na_values=[""])


def load_sample() -> pd.DataFrame:
    """The 403 deals of the analysis sample."""
    table = load_analysis_table()
    sample = table[table["in_analysis_sample"] == 1].copy()
    counts = {"all": len(sample),
              "partial": int((sample["term_partial_tender_offer"] == 1).sum()),
              "pinned": int((sample["price_gap_at_start_pct"].abs() <= PINNED_THRESHOLD_PCT).sum())}
    for name, expected in EXPECTED_SAMPLE_SIZE.items():
        assert counts[name] == expected, (name, counts[name], expected)
    return sample
