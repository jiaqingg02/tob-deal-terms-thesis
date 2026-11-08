"""Load the analysis sample (403 deals) and classify the deals into three groups (Section 4.1).

  deal_group = "partial" : partial tender offer (term_partial_tender_offer = 1)
               "pinned"  : full tender offer with |price gap at start| <= 1%
               "free"    : other full tender offers (the stock price moves freely)

The program stops if the sample sizes differ from those in the paper
(config.EXPECTED_SAMPLE_SIZE).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EXPECTED_SAMPLE_SIZE, PINNED_THRESHOLD_PCT, PROCESSED  # noqa: E402

GROUP_LABELS = {
    "free": "自由に動く全部買付け",
    "pinned": "張り付いた全部買付け",
    "partial": "部分買付け",
}


def load_analysis_table() -> pd.DataFrame:
    """All 413 deals whose documents were read (see code/01_dataprep/06_build_analysis_table.py)."""
    return pd.read_csv(PROCESSED / "analysis_table.csv", index_col=0,
                       dtype={"target_securities_code": str}, keep_default_na=False,
                       na_values=[""])


def classify(table: pd.DataFrame) -> pd.Series:
    partial = table["term_partial_tender_offer"] == 1
    pinned = table["price_gap_at_start_pct"].abs() <= PINNED_THRESHOLD_PCT
    group = pd.Series("free", index=table.index)
    group[~partial & pinned] = "pinned"
    group[partial] = "partial"
    return group


def load_sample() -> pd.DataFrame:
    """The 403 deals of the analysis sample, with the column deal_group."""
    table = load_analysis_table()
    sample = table[table["in_analysis_sample"] == 1].copy()
    sample["deal_group"] = classify(sample)
    counts = sample["deal_group"].value_counts()
    assert len(sample) == EXPECTED_SAMPLE_SIZE["all"], len(sample)
    for g in ("partial", "pinned", "free"):
        assert counts[g] == EXPECTED_SAMPLE_SIZE[g], (g, counts[g])
    return sample
