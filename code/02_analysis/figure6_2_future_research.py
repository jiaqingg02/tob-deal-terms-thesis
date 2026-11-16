"""Figure 6.2: What this thesis analysed and the three directions for future research (diagram, no data).

Upper row (solid boxes): this thesis, deal terms read from the documents -> return from the return start
date to the initial offer end date. Lower row (dashed boxes): the three future questions in Chapter 6,
each placed under the part of the analysis it extends: more information read from the documents (input),
comparing deals by investor attention (the link), and predicting later events (output).

Output  output/figures/figure6_2_future_research.png
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_FIGURES  # noqa: E402
import figure_style  # noqa: F401,E402

W, H = 3.2, 1.25


def box(ax, x, y, text, dashed=False, fill="white"):
    ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H, boxstyle="round,pad=0.02,rounding_size=0.1",
                                facecolor=fill, edgecolor="0.25", lw=1.1, ls="--" if dashed else "-"))
    ax.text(x, y, text, ha="center", va="center", fontsize=11, linespacing=1.6)


def arrow(ax, start, end, dashed=False):
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="-|>", color="0.25", lw=1.1, ls="--" if dashed else "-"))


def main():
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 6)
    ax.axis("off")
    left, mid, right = 2.6, 6.5, 10.2
    top, bottom = 4.6, 1.5

    ax.text(0.2, top, "本稿", fontsize=12, va="center")
    ax.text(0.2, bottom, "今後", fontsize=12, va="center")
    ax.plot([0.15, 11.9], [3.05, 3.05], color="0.6", lw=0.6)

    box(ax, left, top, "書類から読み取った\n取引条件", fill="0.9")
    box(ax, right, top, "収益率\n（計算開始日から\n当初の買付期間末日まで）", fill="0.9")
    arrow(ax, (left + W / 2, top), (right - W / 2, top))
    ax.text(mid, top + 0.25, "関係の推定・予測", ha="center", va="bottom", fontsize=11)

    box(ax, left, bottom, "読み取る情報を増やす\n（特別委員会の審議内容、\n算定結果の範囲）", dashed=True)
    box(ax, mid, bottom, "注目度の高い案件と\n低い案件で比べる", dashed=True)
    box(ax, right, bottom, "その後の出来事を予測する\n（買付価格の引上げ、\n対抗提案）", dashed=True)
    for x, target in [(left, (left, top - H / 2)), (mid, (mid, top - 0.1)), (right, (right, top - H / 2))]:
        arrow(ax, (x, bottom + H / 2), target, dashed=True)
    fig.savefig(OUTPUT_FIGURES / "figure6_2_future_research.png")


if __name__ == "__main__":
    main()
