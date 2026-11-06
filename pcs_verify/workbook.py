from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .counts import split_pos_n


def cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v).replace("\xa0", " ").strip()


@dataclass
class WorkbookRow:
    tissue: str
    pathology: str
    legend_character: str = ""
    pos: str = ""
    n: str = ""
    comments: str = ""


@dataclass
class ParsedWorkbook:
    normal: list[WorkbookRow]
    abnormal: list[WorkbookRow]
    product_name: str | None = None
    file_name: str | None = None


def _norm_header(v: Any) -> str:
    return " ".join(cell(v).lower().split())


def _find_header_map(ws, max_scan: int = 8) -> dict[str, int] | None:
    """Locate Final Table header row and map column names → 1-based indexes."""
    for r in range(1, max_scan + 1):
        mapping: dict[str, int] = {}
        for c in range(1, (ws.max_column or 1) + 1):
            h = _norm_header(ws.cell(r, c).value)
            if not h:
                continue
            if h in {"/", "／"}:
                mapping.setdefault("slash", c)
            elif "tissue" in h and "pathology" not in h:
                mapping.setdefault("tissue", c)
            elif h == "pathology" or h.startswith("pathology"):
                mapping.setdefault("pathology", c)
            elif "legend" in h:
                mapping.setdefault("legend", c)
            elif "comment" in h:
                mapping.setdefault("comments", c)
            elif h in {"#pos", "pos"} or h.startswith("#pos"):
                mapping.setdefault("pos", c)
            elif h in {"n", "#n"} or h.startswith("n "):
                mapping.setdefault("n", c)
            elif h in {"neg", "negative"} or h.startswith("#neg"):
                mapping.setdefault("neg", c)
        if "tissue" in mapping and ("pos" in mapping or "pathology" in mapping):
            mapping["_header_row"] = r
            return mapping
    return None


def _get(ws, row: int, cols: dict[str, int], key: str) -> str:
    c = cols.get(key)
    if not c:
        return ""
    return cell(ws.cell(row, c).value)


def _parse_sheet(ws, *, prefer_legend: bool) -> list[WorkbookRow]:
    cols = _find_header_map(ws)
    rows: list[WorkbookRow] = []
    if not cols:
        return rows
    start = cols["_header_row"] + 1
    for r in range(start, (ws.max_row or start) + 1):
        tissue = _get(ws, r, cols, "tissue")
        if not tissue:
            continue
        if tissue.lower() == "legend" or tissue.lower() == "tissue":
            break
        if tissue.startswith("* Where comments"):
            break
        pathology = _get(ws, r, cols, "pathology")
        legend = _get(ws, r, cols, "legend") if prefer_legend else ""
        pos_raw = _get(ws, r, cols, "pos")
        n_raw = _get(ws, r, cols, "n") or _get(ws, r, cols, "neg")
        pos, n = split_pos_n(pos_raw, n_raw)
        comments = _get(ws, r, cols, "comments")
        rows.append(
            WorkbookRow(
                tissue=tissue,
                pathology=pathology,
                legend_character=legend,
                pos=pos,
                n=n,
                comments=comments,
            )
        )
    return rows


def parse_workbook(path: str | Path) -> ParsedWorkbook:
    path = Path(path)
    # data_only=True uses cached calculated values (needed for formula-driven counts).
    # If Comments were typed as text they appear either way; if formulas weren't cached,
    # fall back to the non-data_only workbook for blank comment cells.
    wb = load_workbook(path, data_only=True, read_only=False)
    wb_raw = load_workbook(path, data_only=False, read_only=False)

    product_name = None
    if "Sign Off Sheet" in wb.sheetnames:
        sign = wb["Sign Off Sheet"]
        for row in sign.iter_rows(min_row=5, max_row=5, min_col=2, max_col=2, values_only=True):
            product_name = cell(row[0]) if row else None
        if product_name == "XXXX (Ensure Clone is referenced)":
            product_name = None

    if "Final Table - Normal" not in wb.sheetnames and "Final Table - Abnormal" not in wb.sheetnames:
        raise ValueError(
            'Could not find "Final Table - Normal" or "Final Table - Abnormal" sheets.'
        )

    normal = (
        _parse_sheet(wb["Final Table - Normal"], prefer_legend=False)
        if "Final Table - Normal" in wb.sheetnames
        else []
    )
    abnormal = (
        _parse_sheet(wb["Final Table - Abnormal"], prefer_legend=True)
        if "Final Table - Abnormal" in wb.sheetnames
        else []
    )

    # Recover Comments that data_only lost (uncached formulas / odd caches)
    if "Final Table - Normal" in wb_raw.sheetnames and normal:
        raw_cols = _find_header_map(wb_raw["Final Table - Normal"])
        if raw_cols and "comments" in raw_cols:
            raw_ws = wb_raw["Final Table - Normal"]
            by_tissue = {r.tissue.lower(): r for r in normal}
            for r in range(raw_cols["_header_row"] + 1, (raw_ws.max_row or 1) + 1):
                tissue = _get(raw_ws, r, raw_cols, "tissue")
                if not tissue:
                    continue
                target = by_tissue.get(tissue.lower())
                if target and not target.comments:
                    raw_c = _get(raw_ws, r, raw_cols, "comments")
                    if raw_c and not raw_c.startswith("="):
                        target.comments = raw_c

    if "Final Table - Abnormal" in wb_raw.sheetnames and abnormal:
        raw_cols = _find_header_map(wb_raw["Final Table - Abnormal"])
        if raw_cols and "comments" in raw_cols:
            raw_ws = wb_raw["Final Table - Abnormal"]
            by_tissue = {r.tissue.lower(): r for r in abnormal}
            for r in range(raw_cols["_header_row"] + 1, (raw_ws.max_row or 1) + 1):
                tissue = _get(raw_ws, r, raw_cols, "tissue")
                if not tissue:
                    continue
                target = by_tissue.get(tissue.lower())
                if target and not target.comments:
                    raw_c = _get(raw_ws, r, raw_cols, "comments")
                    if raw_c and not raw_c.startswith("="):
                        target.comments = raw_c

    return ParsedWorkbook(
        normal=normal,
        abnormal=abnormal,
        product_name=product_name,
        file_name=path.name,
    )
