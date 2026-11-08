"""Numbers quoted in the text of Sections 3.3 and 4.1 (not shown in any table).

Section 4.1 compares the return R_i with the price gap S_i for full offers (339 deals)
and partial offers (64 deals); all counts use the same rules as the text.

Each line prints the number together with the sentence it supports, so the
text can be checked against this output.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUT_TABLES  # noqa: E402
from sample import load_sample  # noqa: E402


def main():
    df = load_sample()
    R, S = df["return_to_initial_end_pct"], df["price_gap_at_start_pct"]
    full, part = df[df.term_partial_tender_offer == 0], df[df.term_partial_tender_offer == 1]
    fR, fS = full["return_to_initial_end_pct"], full["price_gap_at_start_pct"]
    pR, pS = part["return_to_initial_end_pct"], part["price_gap_at_start_pct"]
    full_above, full_below, full_near = full[fS > 1], full[fS < -1], full[fS.abs() <= 1]
    part_above = part[pS > 0]
    lines = [
        ("3.3", "|S_i| <= 1 の案件数（部分買付けを含む）", int((S.abs() <= 1).sum())),
        ("3.3", "-1 <= R_i <= 1 の案件数", int(R.between(-1, 1).sum())),
        ("3.3", "R_i >= 60 の案件数", int((R >= 60).sum())),
        ("3.3", "S_i < -30 の案件数", int((S < -30).sum())),
        ("3.3", "S_i >= 60 の案件数", int((S >= 60).sum())),
        ("4.1", "全部買付けで S_i > 1 の件数 / そのうち |R_i - S_i| <= 1 の件数",
         f"{len(full_above)} / {int((full_above.return_to_initial_end_pct - full_above.price_gap_at_start_pct).abs().le(1).sum())}"),
        ("4.1", "全部買付けで S_i < -1 の件数 / その R_i の中央値",
         f"{len(full_below)} / {full_below.return_to_initial_end_pct.median():.2f}"),
        ("4.1", "部分買付けで S_i > 0 の件数 / そのうち |R_i - S_i| <= 1 の件数",
         f"{len(part_above)} / {int((part_above.return_to_initial_end_pct - part_above.price_gap_at_start_pct).abs().le(1).sum())}"),
        ("4.1", "全部買付けで |S_i| <= 1 の件数 / そのうち |R_i| <= 1 の件数",
         f"{len(full_near)} / {int(full_near.return_to_initial_end_pct.abs().le(1).sum())}"),
        ("4.1", "全部買付けで |S_i| <= 0.5 の件数 / 0.5 < |S_i| <= 1 の件数",
         f"{int((fS.abs() <= 0.5).sum())} / {int(fS.abs().between(0.5, 1, inclusive='right').sum())}"),
    ]
    text = "\n".join(f"[{sec}] {desc}: {val}" for sec, desc, val in lines)
    (OUTPUT_TABLES / "numbers_in_text.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
