#!/usr/bin/env python3
"""Parse PCS Workbook Final Tables (Form9182) to JSON on stdout."""
from __future__ import annotations

import json
import sys
from openpyxl import load_workbook


def cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).replace("\xa0", " ").strip()


def parse_normal(ws):
    rows = []
    for r in range(2, (ws.max_row or 1) + 1):
        tissue = cell(ws.cell(r, 2).value)
        pathology = cell(ws.cell(r, 3).value)
        if not tissue:
            continue
        rows.append(
            {
                "tissue": tissue,
                "pathology": pathology,
                "legendCharacter": "",
                "pos": cell(ws.cell(r, 4).value),
                "n": cell(ws.cell(r, 6).value),
                "comments": cell(ws.cell(r, 7).value),
            }
        )
    return rows


def parse_abnormal(ws):
    rows = []
    for r in range(3, (ws.max_row or 1) + 1):
        tissue = cell(ws.cell(r, 2).value)
        pathology = cell(ws.cell(r, 3).value)
        legend = cell(ws.cell(r, 4).value)
        if tissue.lower() == "legend":
            break
        if tissue.startswith("* Where comments"):
            break
        if not tissue:
            continue
        rows.append(
            {
                "tissue": tissue,
                "pathology": pathology,
                "legendCharacter": legend,
                "pos": cell(ws.cell(r, 5).value),
                "n": cell(ws.cell(r, 7).value),
                "comments": cell(ws.cell(r, 8).value),
            }
        )
    return rows


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: parse_pcs_workbook.py <file.xlsx>"}))
        sys.exit(1)
    path = sys.argv[1]
    # data_only=True reads cached calculated #pos / n values
    wb = load_workbook(path, data_only=True, read_only=True)
    product_name = None
    if "Sign Off Sheet" in wb.sheetnames:
        sign = wb["Sign Off Sheet"]
        # row 5 col 2
        for row in sign.iter_rows(min_row=5, max_row=5, min_col=2, max_col=2, values_only=True):
            product_name = cell(row[0]) if row else None
        if product_name == "XXXX (Ensure Clone is referenced)":
            product_name = None

    normal = parse_normal(wb["Final Table - Normal"]) if "Final Table - Normal" in wb.sheetnames else []
    abnormal = (
        parse_abnormal(wb["Final Table - Abnormal"])
        if "Final Table - Abnormal" in wb.sheetnames
        else []
    )
    if not normal and not abnormal:
        print(
            json.dumps(
                {
                    "error": 'Could not find "Final Table - Normal" or "Final Table - Abnormal" sheets.'
                }
            )
        )
        sys.exit(2)

    print(
        json.dumps(
            {
                "normal": normal,
                "abnormal": abnormal,
                "productName": product_name or None,
            }
        )
    )


if __name__ == "__main__":
    main()
