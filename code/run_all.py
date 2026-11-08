"""Run every program from the raw data to the tables and figures of the paper, in order.

Usage:  python code/run_all.py
"""
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
PROGRAMS = [
    # data preparation
    ("01_dataprep", "00_cut_document_passages.py"),
    ("01_dataprep", "01_compute_price_gap.py"),
    ("01_dataprep", "02_compute_return_to_initial_end.py"),
    ("01_dataprep", "03_compute_sentiment_scores.py"),
    ("01_dataprep", "04_extract_deal_terms.py"),
    ("01_dataprep", "05_compute_attention_measures.py"),
    ("01_dataprep", "06_build_analysis_table.py"),
    ("01_dataprep", "07_check_offer_prices.py"),
    ("01_dataprep", "08_export_published_data.py"),
    # tables and figures (Chapters 3 and 4)
    ("02_analysis", "table3_1_sample_selection.py"),
    ("02_analysis", "table3_2_and_3_3_deals_by_year_and_descriptive_statistics.py"),
    ("02_analysis", "figure3_1_return_and_price_gap_distribution.py"),
    ("02_analysis", "appendix_a_agreement_with_ai.py"),
    ("02_analysis", "figure4_1_price_gap_and_return.py"),
    ("02_analysis", "figure4_2_return_before_and_after_log.py"),
    ("02_analysis", "numbers_in_text.py"),
    # results (Chapter 5; all use the one equation in equation.py)
    ("02_analysis", "table5_regressions.py", "R1"),
    ("02_analysis", "table5_regressions.py", "W1"),
    ("02_analysis", "table5_regressions.py", "R1", "--include-boundary-deals"),
    ("02_analysis", "table5_prediction_errors.py", "R1"),
    ("02_analysis", "table5_prediction_errors.py", "W1"),
    ("02_analysis", "table5_attention.py"),
    ("02_analysis", "robustness_thresholds.py"),
    # Appendix C
    ("02_analysis", "figureC1_absolute_price_gap_distribution.py"),
]

for folder, program, *arguments in PROGRAMS:
    print(f"==== {folder}/{program} {' '.join(arguments)}", flush=True)
    subprocess.run([sys.executable, str(CODE / folder / program), *arguments], cwd=CODE / folder, check=True)
