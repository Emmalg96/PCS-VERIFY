#!/usr/bin/env python3
"""Build a sample approved-workbook PDF (Sign Off + Final Tables) for demos."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pcs_verify.demo import DEMO_WORKBOOK_ABNORMAL, DEMO_WORKBOOK_NORMAL

OUT = ROOT / "public" / "samples" / "PCS_WORKBOOK_FINAL_TABLES.pdf"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUT), pagesize=A4)
    story = []

    story.append(Paragraph("PCS Workbook (NCL-FRM-001659) — Approved PDF extract", styles["Title"]))
    story.append(Paragraph("Product: Demo Antibody (Clone A)", styles["Normal"]))
    story.append(
        Paragraph(
            "Attachment set per NCL-WI-000277 §3.7.8: Sign Off Sheet, "
            "Final Table – Normal, Final Table – Abnormal.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))

    story.append(Paragraph("Sign Off Sheet", styles["Heading1"]))
    story.append(Paragraph("Status: Approved (sample demo — not a controlled record).", styles["Normal"]))
    story.append(Spacer(1, 18))

    story.append(Paragraph("Final Table – Normal", styles["Heading1"]))
    normal_data = [["Tissue", "Pathology", "#pos", "n", "Comments"]]
    for r in DEMO_WORKBOOK_NORMAL:
        normal_data.append([r.tissue, r.pathology, r.pos, r.n, r.comments])
    t1 = Table(normal_data, colWidths=[160, 80, 40, 40, 140])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2dd")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(t1)
    story.append(Spacer(1, 24))

    story.append(Paragraph("Final Table – Abnormal", styles["Heading1"]))
    ab_data = [["Tissue", "Pathology", "Legend", "#pos", "n", "Comments"]]
    for r in DEMO_WORKBOOK_ABNORMAL:
        ab_data.append(
            [r.tissue, r.pathology, r.legend_character, r.pos, r.n, r.comments]
        )
    t2 = Table(ab_data, colWidths=[100, 120, 45, 40, 40, 120])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2dd")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(t2)

    doc.build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
