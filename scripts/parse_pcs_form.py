#!/usr/bin/env python3
"""Extract PCS Form (NCL-FRM-000146) tissue tables 3/4 from a .docx to JSON."""
from __future__ import annotations

import json
import re
import sys
from docx import Document


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def header_map(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, raw in enumerate(cells):
        h = norm(raw).lower()
        if not h:
            continue
        if "tissue" in h and "pathology" not in h and i not in mapping.values():
            mapping.setdefault("tissue", i)
        elif h == "pathology" or h.startswith("pathology"):
            mapping.setdefault("pathology", i)
        elif "legend" in h:
            mapping.setdefault("legend", i)
        elif h in {"#pos", "pos", "# positive", "positive"} or h.startswith("#pos"):
            mapping.setdefault("pos", i)
        elif h == "n" or h.startswith("n ") or h == "total":
            mapping.setdefault("n", i)
        elif "pos" in h and "/" in h:
            mapping.setdefault("ratio", i)
        elif "comment" in h:
            mapping.setdefault("comments", i)
    return mapping


def is_tissue_table(header_cells: list[str]) -> bool:
    headers = [norm(c).lower() for c in header_cells]
    joined = " ".join(headers)
    has_tissue = any(h == "tissue" or h.startswith("tissue ") for h in headers)
    has_pathology = any("pathology" in h for h in headers)
    has_pos = any(
        h in {"#pos", "pos", "n"} or h.startswith("#pos") or "pos/" in h or h == "#pos/n"
        for h in headers
    )
    # Exclude control recommendation tables (Positive Control Tissue / Negative Control Tissue)
    if "control tissue" in joined:
        return False
    return has_tissue and (has_pathology or has_pos)


def row_from_cells(cells: list[str], colmap: dict[str, int]) -> dict | None:
    def get(key: str) -> str:
        idx = colmap.get(key)
        if idx is None or idx >= len(cells):
            return ""
        return norm(cells[idx])

    tissue = get("tissue")
    pathology = get("pathology")
    if not tissue and not pathology:
        return None
    # skip repeated header-like rows
    if tissue.lower() == "tissue" and "pathology" in pathology.lower():
        return None

    pos = get("pos")
    n = get("n")
    comments = get("comments")
    legend = get("legend")

    if "ratio" in colmap:
        ratio = get("ratio")
        m = re.match(r"^(\d+)\s*/\s*(\d+)$", ratio)
        if m:
            pos, n = m.group(1), m.group(2)

    # Excel paste sometimes keeps '/' as its own column — handled by caller widths
    if legend and legend not in pathology:
        # If legend column still present (pre-merge), append for form-expected view
        pathology = f"{pathology}{legend}" if pathology else legend

    return {
        "tissue": tissue,
        "pathology": pathology,
        "pos": pos,
        "n": n,
        "comments": comments,
    }


def classify_kind(paragraphs_before: str, rows: list[dict]) -> str:
    text = paragraphs_before.lower()
    if "abnormal tissue" in text or "table 4" in text:
        return "abnormal"
    if "normal tissue" in text or "table 3" in text:
        return "normal"
    # Heuristic: all pathology == Normal => normal table
    paths = [r["pathology"].lower() for r in rows if r.get("pathology")]
    if paths and all(p == "normal" or p.startswith("normal") for p in paths):
        return "normal"
    return "abnormal"


def parse_docx(path: str) -> dict:
    doc = Document(path)
    body_paras = [norm(p.text) for p in doc.paragraphs]

    # Walk document elements in order to associate headings with tables
    # python-docx doesn't expose easy mixed iter on Document; approximate via
    # table index and preceding paragraph scan using XML order.
    from docx.oxml.ns import qn

    normal: list[dict] = []
    abnormal: list[dict] = []
    found_tables = 0
    warnings: list[str] = []

    preceding: list[str] = []
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            texts = [node.text for node in child.iter(qn("w:t")) if node.text]
            t = norm("".join(texts))
            if t:
                preceding.append(t)
            continue
        if child.tag != qn("w:tbl"):
            continue

        # match table object by order
        table = doc.tables[found_tables]
        found_tables += 1
        if not table.rows:
            continue
        header_cells = [norm(c.text) for c in table.rows[0].cells]
        if not is_tissue_table(header_cells):
            preceding = []
            continue

        colmap = header_map(header_cells)
        if "tissue" not in colmap:
            warnings.append(f"Tissue table skipped (no Tissue column): {header_cells}")
            preceding = []
            continue

        rows: list[dict] = []
        for row in table.rows[1:]:
            cells = [norm(c.text) for c in row.cells]
            # Deduplicate merged-cell repeats: python-docx repeats merged values
            parsed = row_from_cells(cells, colmap)
            if parsed:
                rows.append(parsed)

        if not rows:
            preceding = []
            continue

        kind = classify_kind(" ".join(preceding[-8:]), rows)
        if kind == "normal":
            normal.extend(rows)
        else:
            abnormal.extend(rows)
        preceding = []

    if not normal and not abnormal:
        return {
            "error": "No tissue tables found (expected Table 3 Normal / Table 4 Abnormal with Tissue and Pathology columns).",
            "normal": [],
            "abnormal": [],
            "warnings": warnings,
        }

    return {
        "normal": normal,
        "abnormal": abnormal,
        "warnings": warnings,
        "tableCount": found_tables,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: parse_pcs_form.py <file.docx>"}))
        sys.exit(1)
    try:
        result = parse_docx(sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}))
        sys.exit(2)
    print(json.dumps(result))
    if result.get("error"):
        sys.exit(3)


if __name__ == "__main__":
    main()
