#!/usr/bin/env python3
"""Build a tiny legacy Pos/Neg sample form for uprev testing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from docx import Document

from pcs_verify.demo import DEMO_WORKBOOK_ABNORMAL, DEMO_WORKBOOK_NORMAL

OUT = ROOT / "public" / "samples" / "PCS_FORM_LEGACY_POS_NEG.docx"


def main() -> None:
    doc = Document()
    doc.add_heading("Product Claims Summary (legacy count columns)", level=1)
    doc.add_paragraph("Sample pre-Form9182 style tables for uprev testing.")
    doc.add_heading("Normal Tissue Staining", level=2)
    doc.add_paragraph("Table 3: Normal tissue staining (legacy Pos / Neg)")
    t3 = doc.add_table(rows=1 + len(DEMO_WORKBOOK_NORMAL), cols=5)
    t3.style = "Table Grid"
    for i, h in enumerate(["Tissue", "Pos", "/", "Neg", "Comments"]):
        t3.rows[0].cells[i].text = h
    for ri, r in enumerate(DEMO_WORKBOOK_NORMAL, start=1):
        # Legacy demo: Neg column holds what modern `n` holds (rename-style)
        t3.rows[ri].cells[0].text = r.tissue
        t3.rows[ri].cells[1].text = r.pos
        t3.rows[ri].cells[2].text = "/"
        t3.rows[ri].cells[3].text = r.n
        t3.rows[ri].cells[4].text = r.comments

    doc.add_heading("Abnormal Tissue Staining", level=2)
    doc.add_paragraph("Table 4: Abnormal tissue staining (legacy Pos / Neg)")
    t4 = doc.add_table(rows=1 + len(DEMO_WORKBOOK_ABNORMAL), cols=5)
    t4.style = "Table Grid"
    for i, h in enumerate(["Tissue", "Pathology", "Pos", "/", "Neg"]):
        t4.rows[0].cells[i].text = h
    for ri, r in enumerate(DEMO_WORKBOOK_ABNORMAL, start=1):
        t4.rows[ri].cells[0].text = r.tissue
        t4.rows[ri].cells[1].text = f"{r.pathology}{r.legend_character}"
        t4.rows[ri].cells[2].text = r.pos
        t4.rows[ri].cells[3].text = "/"
        t4.rows[ri].cells[4].text = r.n

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
