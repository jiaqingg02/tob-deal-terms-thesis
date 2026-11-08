"""Convert the disclosure documents to text and cut out the passages for each deal term.

Deals (data/inputs/deals_with_document_passages.csv)
  documents = "edinet"                   339 deals announced in 2022 or later: the tender offer registration statement
                                         and the opinion statement (EDINET PDF)
  documents = "tdnet_timely_disclosure"  114 deals announced in 2019 and 2021 (and 2020, not analysed): the timely
                                         disclosures of the start of the offer and of the opinion (TDnet PDF)

Steps
  1. Text of the documents
     - registration statement: `pdftotext -layout` (Poppler) -> data/processed/document_text/edinet/<document id>.txt
     - opinion statement: read directly from the PDF with PyMuPDF
     - timely disclosures: PyMuPDF. For PDFs whose default reading order mixes columns, the text is read again in
       sorted order and the sorted text is used when common words (公開買付, といいます, 本公開買付価格, 取締役会)
       appear at least 1.3 times as often and at least 5 more times -> data/processed/document_text/tdnet/<id>.txt
  2. Passages (document_passage_cutting.py): 7 passages of the registration statement and 4 of the opinion statement,
     with the names of the target and the acquirer and the securities code replaced by "■■"
     -> data/processed/document_passages/registration/<deal id>.txt and .../opinion/<deal id>.txt

The passages are the same as those read by the earlier generative-AI judgments: re-running this program on the
same PDFs gave identical files for all 906 passage files that were used (checked on 2026-11-08).
"""
import subprocess
import sys
import unicodedata
from pathlib import Path

import fitz
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INPUTS, PROCESSED, RAW_DATA  # noqa: E402
import document_passage_cutting as cut  # noqa: E402

EDINET_PDF = RAW_DATA / "data" / "edinet_pdf"
TDNET_PDF = RAW_DATA / "data_old" / "pdf"
TEXT = PROCESSED / "document_text"
PASSAGES = PROCESSED / "document_passages"
COMMON_WORDS = ["公開買付", "といいます", "本公開買付価格", "取締役会"]


def registration_text(document_id):
    """Text of an EDINET registration statement, made with `pdftotext -layout` and then cleaned."""
    if not isinstance(document_id, str) or not document_id:
        return ""
    out = TEXT / "edinet" / f"{document_id}.txt"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdftotext", "-layout", str(EDINET_PDF / f"{document_id}.pdf"), str(out)], check=True)
    return cut.clean(open(out, encoding="utf-8", errors="ignore").read())


def opinion_text(document_id):
    """Text of an EDINET opinion statement, read with PyMuPDF and then cleaned."""
    if not isinstance(document_id, str) or not document_id:
        return ""
    pdf = EDINET_PDF / f"{document_id}.pdf"
    return cut.clean("".join(page.get_text() for page in fitz.open(pdf))) if pdf.exists() else ""


def timely_disclosure_text(document_id):
    """Text of a TDnet timely disclosure (PyMuPDF; sorted reading order when it is clearly more readable)."""
    if not document_id:
        return ""
    out = TEXT / "tdnet" / f"{document_id}.txt"
    pdf = TDNET_PDF / f"{document_id}.pdf"
    if not out.exists() and pdf.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        plain = "".join(page.get_text() for page in fitz.open(pdf))
        ordered = "".join(page.get_text(sort=True) for page in fitz.open(pdf))
        score = lambda t: sum(cut.re.sub(r"\s+", "", unicodedata.normalize("NFKC", t)).count(w) for w in COMMON_WORDS)
        out.write_text(ordered if score(ordered) > score(plain) * 1.3 and score(ordered) - score(plain) >= 5 else plain)
    return cut.clean(open(out, errors="ignore").read()) if out.exists() else ""


def write(kind, deal_id, note, sections):
    folder = PASSAGES / kind
    folder.mkdir(parents=True, exist_ok=True)
    text = f"案件ID: {deal_id}\n資料: {note}\n"
    for name, (label, body) in sections.items():
        text += f"\n==== [{name}] {label} ====\n" + (body or "（該当する段落が見つからなかった）\n")
    (folder / f"{deal_id}.txt").write_text(text)


def edinet_deals(deal_ids):
    prepared = pd.read_csv(INPUTS / "prepared_data_corrected.csv", dtype={"code": str}, keep_default_na=False)
    prepared.index = prepared.code + "_" + prepared.event_date
    deals = pd.read_csv(RAW_DATA / "data" / "tob_deals.csv", dtype={"target_code": str})
    deals["key"] = deals.target_code + "_" + deals.first_date
    deals = deals.sort_values("edinet_iken").drop_duplicates("key").set_index("key")
    for deal_id in deal_ids:
        row = prepared.loc[deal_id]
        code = deal_id.split("_")[0]
        # registration statement passages (opinion statement used for the board passage)
        T = registration_text(row.edinet_todokede)
        I = opinion_text(row.edinet_iken)
        names = sorted(set(cut.names(T) + cut.names(I)), key=len, reverse=True)
        T, I = cut.mask(T, names, code), cut.mask(I, names, code)
        write("registration", deal_id, "公開買付届出書・意見表明報告書（名称は■■で伏せてある）",
              {k: (cut.JP[k], f(T, I)) for k, f in cut.THEMES.items()})
        # opinion statement passages (documents as listed in tob_deals.csv)
        r = deals.loc[deal_id] if deal_id in deals.index else None
        T = registration_text(r.edinet_todokede) if r is not None and isinstance(r.edinet_todokede, str) else ""
        I = opinion_text(r.edinet_iken) if r is not None and isinstance(r.edinet_iken, str) else ""
        names = sorted(set(cut.names(T) + cut.names(I)), key=len, reverse=True)
        T, I = cut.mask(T, names, code), cut.mask(I, names, code)
        write("opinion", deal_id, "意見表明報告書・公開買付届出書（名称・証券コードは■■で伏せてある）",
              {k: (label, f(I, T)) for k, (f, label) in cut.TH.items()})


def timely_disclosure_deals(deal_ids):
    deals = pd.read_csv(RAW_DATA / "data_old" / "tob_deals.csv", dtype=str, keep_default_na=False)
    deals["key"] = deals.target_code + "_" + deals.first_date
    deals = deals[deals.status == ""].set_index("key")
    for deal_id in deal_ids:
        d = deals.loc[deal_id]
        code = deal_id.split("_")[0]
        T, I = timely_disclosure_text(d.edinet_todokede), timely_disclosure_text(d.edinet_iken)
        hint = cut.re.sub(r"^[ＪＭＰＱＲ]－", "", d.target_name_hint)
        names = cut.names_old(T, I, [d.target_name, unicodedata.normalize("NFKC", d.target_name),
                                     hint, unicodedata.normalize("NFKC", hint)])
        T, I = cut.mask(T, names, code), cut.mask(I, names, code)
        write("registration", deal_id, "公開買付けの開始に関するお知らせ・意見表明に関するお知らせ（適時開示。名称は■■で伏せてある）",
              {k: (cut.JP[k], f(T, I)) for k, f in cut.THEMES.items()})
        write("opinion", deal_id, "意見表明に関するお知らせ・公開買付けの開始に関するお知らせ（適時開示。名称は■■で伏せてある）",
              {k: (label, f(I, T)) for k, (f, label) in cut.TH.items()})


def main():
    deals = pd.read_csv(INPUTS / "deals_with_document_passages.csv")
    edinet_deals(deals.deal_id[deals.documents == "edinet"])
    timely_disclosure_deals(deals.deal_id[deals.documents == "tdnet_timely_disclosure"])
    for kind in ["registration", "opinion"]:
        print(kind, len(list((PASSAGES / kind).glob("*.txt"))), "files")


if __name__ == "__main__":
    main()
