"""Figure 3.2: How the deal terms are judged from the two disclosure documents.

The figure shows the actual steps of code/01_dataprep/04_extract_deal_terms.py:
(1) relevant passages are cut out of the documents by headings and keywords, and the full text is read
    only for the acquirer type and for one kind of competing-bid statement;
(2) hand-written rules (expressions, negations and numbers) give 1, 0 or missing with the evidence;
(3) values found to be wrong when checked against the original documents are corrected
    (corrections_after_document_check.csv).
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402  (font settings)


def box(ax, x, y, w, h, text, shaded=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                fc="0.93" if shaded else "white", ec="black", lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=12, linespacing=1.6)


def arrow(ax, start, end):
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="->", lw=1.2, color="black", mutation_scale=14))


def main():
    fig, ax = plt.subplots(figsize=(11.0, 6.4))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    box(ax, 2.5, 5.3, 6.0, 0.9, "公開買付届出書・意見表明報告書\n（計算開始日の15時までに提出されたもの）", shaded=True)
    box(ax, 0.5, 3.6, 4.8, 1.1, "見出しと語句を手掛かりに\n関連する箇所を抜き出す\n（価格交渉の経緯、株主との合意など）")
    box(ax, 5.7, 3.6, 4.8, 1.1, "書類の全文を読む\n（買付者の種類、\n売主による売却先の選定）")
    box(ax, 1.5, 1.95, 8.0, 1.05, "条件ごとに定めた規則を当てはめる\n（該当する表現、否定・仮定の文の除外、数値の比較）")
    box(ax, 1.5, 0.3, 8.0, 1.05, "各条件の値（1・0、資金の記載がない場合は欠測）と根拠の文\n原文と照らして誤りが見つかった判定は修正する", shaded=True)

    arrow(ax, (4.2, 5.3), (2.9, 4.7))
    arrow(ax, (6.8, 5.3), (8.1, 4.7))
    arrow(ax, (2.9, 3.6), (4.2, 3.0))
    arrow(ax, (8.1, 3.6), (6.8, 3.0))
    arrow(ax, (5.5, 1.95), (5.5, 1.35))

    fig.savefig(OUTPUT_FIGURES / "figure3_2_how_deal_terms_are_judged.png")
    print("saved", OUTPUT_FIGURES / "figure3_2_how_deal_terms_are_judged.png")


if __name__ == "__main__":
    main()
