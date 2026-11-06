#!/usr/bin/env python3
"""Build sample filled Product Claims Summary .docx files for demos."""
from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.shared import Pt


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.size = Pt(14 if level == 1 else 12)


def add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]]) -> None:
    doc.add_paragraph(title)
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            table.rows[r_i + 1].cells[c_i].text = val


HEADERS = ["Tissue", "Pathology", "#pos", "n", "Comments"]

NORMAL_MATCH = [
    ["Cerebrum (grey matter tissue)", "Normal", "0", "3", ""],
    ["Tonsil", "Normal", "3", "3", "Lymphocytes positive"],
    ["Liver", "Normal", "0", "3", ""],
    ["Colon", "Normal", "2", "3", "Focal epithelial staining"],
]

ABNORMAL_MATCH = [
    ["Colon", "Adenocarcinoma*", "5", "5", "Membranous staining"],
    ["Breast", "Invasive ductal carcinoma†", "4", "5", ""],
]

NORMAL_ERRORS = [
    ["Cerebrum (grey matter tissue)", "Normal", "0", "3", ""],
    ["Tonsil", "Normal", "2", "3", "Lymphocytes positive"],  # wrong #pos
    ["Liver", "Normal", "0", "3", ""],
    # Colon missing
]

ABNORMAL_ERRORS = [
    ["Colon", "Adenocarcinoma", "5", "5", "Membranous staining"],  # missing *
    ["Breast", "Invasive ductal carcinoma†", "4", "5", ""],
    ["Lung", "Squamous cell carcinoma", "1", "1", ""],  # extra
]


def build(path: Path, normal: list[list[str]], abnormal: list[list[str]], label: str) -> None:
    doc = Document()
    doc.add_heading("Product Claims Summary (sample)", 0)
    doc.add_paragraph(
        f"Sample filled NCL-FRM-000146 tissue tables for PCS verification demos ({label})."
    )
    add_heading(doc, "4.1 Normal Tissue Staining", 2)
    doc.add_paragraph("Table 3: Normal tissue staining for Demo Antibody (Clone A)")
    add_table(doc, "", HEADERS, normal)
    add_heading(doc, "4.2 Abnormal Tissue Staining", 2)
    doc.add_paragraph("Table 4: Abnormal tissue staining for Demo Antibody (Clone A)")
    add_table(doc, "", HEADERS, abnormal)
    doc.add_paragraph(
        "Note: Legend characters are included in the Pathology column per form instructions."
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    print("wrote", path)


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "public" / "samples"
    build(root / "PCS_FORM_TABLES_MATCH.docx", NORMAL_MATCH, ABNORMAL_MATCH, "clean match")
    build(root / "PCS_FORM_TABLES_ERRORS.docx", NORMAL_ERRORS, ABNORMAL_ERRORS, "with errors")


if __name__ == "__main__":
    main()
