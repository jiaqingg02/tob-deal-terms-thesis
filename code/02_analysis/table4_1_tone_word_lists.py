"""Table 4.1: Positive and negative words used for the tone T_i (equation 4.3).

The word lists are read from code/01_dataprep/03_compute_sentiment_scores.py, where
they are defined once, so the table always shows the lists actually used.
"""
import ast
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_TABLES  # noqa: E402

SOURCE = Path(__file__).resolve().parents[1] / "01_dataprep" / "03_compute_sentiment_scores.py"
ROWS = [("報道の見出し", "NEWS_POSITIVE", "NEWS_NEGATIVE"),
        ("意見表明報告書", "OPINION_POSITIVE", "OPINION_NEGATIVE")]


def word_list(text, name):
    """Return the list assigned as  NAME = "w1 w2 ...".split()  in the source."""
    m = re.search(rf'^{name}\s*=\s*("[^"]*")\.split\(\)', text, flags=re.M)
    assert m, name
    return ast.literal_eval(m.group(1)).split()


def main():
    text = SOURCE.read_text(encoding="utf-8")
    rows = []
    for document, pos, neg in ROWS:
        p, n = word_list(text, pos), word_list(text, neg)
        rows.append({"文章": document,
                     "肯定的な語": "、".join(p), "肯定的な語の数": len(p),
                     "否定的な語": "、".join(n), "否定的な語の数": len(n)})
    table = pd.DataFrame(rows)
    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUTPUT_TABLES / "table4_1_tone_word_lists.csv", index=False, encoding="utf-8-sig")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
