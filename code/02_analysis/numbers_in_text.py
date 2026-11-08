"""Numbers quoted in the text of Sections 3.3 and 4.1 (not shown in any table).

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
    pin, free, part = (df[df["deal_group"] == g] for g in ("pinned", "free", "partial"))
    lines = [
        ("3.3", "|S_i| <= 1 の案件数（部分買付けを含む）", int((S.abs() <= 1).sum())),
        ("3.3", "-1 <= R_i <= 1 の案件数", int(R.between(-1, 1).sum())),
        ("3.3", "R_i >= 60 の案件数", int((R >= 60).sum())),
        ("3.3", "S_i < -30 の案件数", int((S < -30).sum())),
        ("3.3", "S_i >= 60 の案件数", int((S >= 60).sum())),
        ("4.1", "全部買付けで |S_i| <= 0.5 の件数", int((df[df.term_partial_tender_offer == 0]["price_gap_at_start_pct"].abs() <= 0.5).sum())),
        ("4.1", "全部買付けで 0.5 < |S_i| <= 1 の件数",
         int(df[df.term_partial_tender_offer == 0]["price_gap_at_start_pct"].abs().between(0.5, 1, inclusive="right").sum())),
        ("4.1", "張り付いた全部買付けで -1 <= R_i <= 1 の件数", int(pin["return_to_initial_end_pct"].between(-1, 1).sum())),
        ("4.1", "自由に動く全部買付けで |R_i - S_i| <= 1 の件数", int(((free["return_to_initial_end_pct"] - free["price_gap_at_start_pct"]).abs() <= 1).sum())),
        ("4.1", "自由に動く全部買付けで S_i > 1 / S_i < -1 の件数",
         f"{int((free['price_gap_at_start_pct'] > 1).sum())} / {int((free['price_gap_at_start_pct'] < -1).sum())}"),
        ("4.1", "部分買付けで S_i > 0 の件数", int((part["price_gap_at_start_pct"] > 0).sum())),
        ("4.1", "部分買付けで S_i > 0 の R_i 平均", round(part.loc[part["price_gap_at_start_pct"] > 0, "return_to_initial_end_pct"].mean(), 2)),
    ]
    text = "\n".join(f"[{sec}] {desc}: {val}" for sec, desc, val in lines)
    (OUTPUT_TABLES / "numbers_in_text.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
