# 書類から抜き出した段落を読み込む
#
# 目的：deal_term_rules.py の判定の入力を作る。段落は 00_cut_document_passages.py が書類から語句と見出しで
#       機械的に抜き出し、社名などを「■■」で伏せたものである（生成AIの判定に用いた段落と同一）。
# 入力：data/processed/document_passages/registration/<案件 key>.txt … 届出書（2019・2021年は開始の適時開示）の7段落
#       data/processed/document_passages/opinion/<案件 key>.txt      … 意見表明報告書（2019・2021年は意見表明の適時開示）の4段落
# 出力：ファイルは出力しない。load() が {案件 key: {段落の名前: 本文}} を返す。
#       届出書の7段落：price / rival / board / shareholder / funding / regulatory / structure
#       意見表明の4段落：committee / policy / valuation / mom（各段落の内容は deal_term_rules.py の冒頭を参照）
import glob
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED  # noqa: E402

PASSAGES = PROCESSED / "document_passages"


def secs(t):
    """「==== [段落の名前] … ====」の見出しで区切られたテキストを {段落の名前: 本文} にする。"""
    out = {}
    parts = re.split(r'==== \[(\w+)\][^\n]*====', t)
    for i in range(1, len(parts), 2):
        out[parts[i]] = parts[i + 1].strip()
    return out


def load():
    """全案件の段落を読み込み、{案件 key: {段落の名前: 本文, '_key': 案件 key}} を返す。

    届出書と意見表明の段落は、同じ案件 key の下にまとめる。"""
    C = {}
    for kind in ["registration", "opinion"]:
        for f in glob.glob(str(PASSAGES / kind / "*.txt")):
            C.setdefault(os.path.basename(f)[:-4], {}).update(secs(open(f).read()))
    for k in C:
        C[k]['_key'] = k
    return C
