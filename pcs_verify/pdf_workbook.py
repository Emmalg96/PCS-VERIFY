"""Extract Final Table – Normal / Abnormal from an approved PCS Workbook PDF.

Per NCL-WI-000277 Rev 6 §3.7.8 the controlled PDF typically includes Sign Off,
Final Table – Normal, and Final Table – Abnormal only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO, Union

import pdfplumber

from .counts import (
    split_pos_n,
    looks_like_pathology_not_comment,
    looks_like_tissue_descriptor_not_comment,
    is_not_included,
    tissue_line_match,
    longest_tissue_for_line,
    scrub_comments,
)
from .workbook import ParsedWorkbook, WorkbookRow
from .form import is_legend_footer_row, is_legend_symbol_line, join_legend_footer_lines

PathLike = Union[str, Path, BinaryIO]


def cell(v) -> str:
    """Normalize a PDF/table cell value to plain text (local copy — always available)."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v).replace("\xa0", " ").strip()


def _norm(s: str) -> str:
    return " ".join((s or "").replace("\xa0", " ").strip().lower().split())


def _looks_like_count(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    if v in {"/", "／", "⁄"}:
        return True
    if re.fullmatch(r"\d+", v):
        return True
    if re.fullmatch(r"\d+\s*[/／⁄]\s*\d+", v):
        return True
    return False


def _map_header(row: list[str | None]) -> dict[str, int] | None:
    """Map header cells to fields — tolerant of '#pos / n', 'Comments', etc."""
    mapping: dict[str, int] = {}
    for i, raw in enumerate(row or []):
        h = _norm(cell(raw))
        if not h:
            continue
        if h in {"/", "／"}:
            mapping.setdefault("slash", i)
            continue
        if "tissue" in h and "pathology" not in h and "control" not in h:
            mapping.setdefault("tissue", i)
        elif h == "pathology" or h.startswith("pathology"):
            mapping.setdefault("pathology", i)
        elif "legend" in h:
            mapping.setdefault("legend", i)
        elif "comment" in h or h in {"notes", "note"}:
            mapping.setdefault("comments", i)
        elif h in {"#pos/n", "#pos / n", "pos/n", "pos / n"} or (
            "pos" in h and "/" in h and "n" in h
        ):
            mapping.setdefault("ratio", i)
        elif h in {"#pos", "pos"} or h.startswith("#pos"):
            mapping.setdefault("pos", i)
        elif h in {"n", "#n"} or h.startswith("n "):
            mapping.setdefault("n", i)
        elif h in {"neg", "negative", "#neg"} or h.startswith("#neg"):
            mapping.setdefault("neg", i)
    if "tissue" in mapping and (
        "pathology" in mapping or "pos" in mapping or "ratio" in mapping
    ):
        return mapping
    return None


def _row_values(row: list[str | None], cols: dict[str, int]) -> WorkbookRow | None:
    def get(field: str) -> str:
        if field not in cols or cols[field] >= len(row):
            return ""
        return cell(row[cols[field]])

    tissue = get("tissue")
    if not tissue:
        return None
    low = tissue.lower()
    if low == "legend" or tissue.startswith("* Where"):
        return None
    # Legend footer: "* Reed-Sternberg cells", "† Immune cells", "=" etc.
    if is_legend_symbol_line(tissue):
        return None
    # Continuation of a wrapped legend meaning (e.g. "and immune cells")
    if tissue[:1].islower() and not get("pathology") and not get("pos") and not get("n"):
        return None

    pos = get("pos")
    n = get("n") or get("neg")
    if "ratio" in cols:
        ratio = get("ratio")
        if ratio:
            pos, n = split_pos_n(ratio, n)
    else:
        pos, n = split_pos_n(pos, n)

    comments = get("comments")
    used = {cols[k] for k in cols}
    # Recover Comments when pdfplumber drops the header or shifts columns
    if not comments:
        candidates: list[str] = []
        for i, raw in enumerate(row or []):
            if i in used:
                continue
            v = cell(raw)
            if not v or _looks_like_count(v):
                continue
            if v.lower() in {"normal", "abnormal"}:
                continue
            if looks_like_pathology_not_comment(v):
                continue
            if looks_like_tissue_descriptor_not_comment(v):
                continue
            candidates.append(v)
        if candidates:
            comments = candidates[-1]
        else:
            for i in range(len(row or []) - 1, -1, -1):
                if i == cols.get("tissue"):
                    break
                if i in {
                    cols.get("pathology"),
                    cols.get("pos"),
                    cols.get("n"),
                    cols.get("neg"),
                    cols.get("ratio"),
                    cols.get("slash"),
                    cols.get("legend"),
                }:
                    continue
                v = cell(row[i])
                if v and not _looks_like_count(v) and v.lower() not in {
                    "normal",
                    "abnormal",
                } and not looks_like_pathology_not_comment(v) and not looks_like_tissue_descriptor_not_comment(v):
                    comments = v
                    break

    if looks_like_pathology_not_comment(comments):
        comments = ""
    if looks_like_tissue_descriptor_not_comment(comments):
        comments = ""
    comments = scrub_comments(comments, tissue)

    return WorkbookRow(
        tissue=tissue,
        pathology=get("pathology"),
        legend_character=get("legend"),
        pos=pos,
        n=n,
        comments=comments,
    )


def _classify_page_text(text: str) -> str | None:
    """Classify a workbook PDF page as Final Table Normal / Abnormal.

    Prefer explicit Final Table / Tissue Staining headings. Bare
    'Normal Tissue' / 'Abnormal Tissue' side labels are handled per-table
    via geometry (they often sit to the left of the grid, not above it).
    """
    t = _norm(text)
    has_ft_abn = bool(re.search(r"final\s+table\s*[–\-]?\s*abnormal", t))
    has_ft_norm = bool(re.search(r"final\s+table\s*[–\-]?\s*normal", t))
    if has_ft_abn and has_ft_norm:
        return None  # both on one page — classify per table
    if has_ft_abn:
        return "abnormal"
    if has_ft_norm:
        return "normal"
    if re.search(r"\babnormal\s+tissue\s+staining\b", t):
        return "abnormal"
    if re.search(r"\bnormal\s+tissue\s+staining\b", t):
        return "normal"
    # Side-label phrases only when exactly one kind appears on the page
    has_abn = bool(re.search(r"\babnormal\s+tissues?\b", t))
    has_norm = bool(re.search(r"\bnormal\s+tissues?\b", t))
    if has_abn and not has_norm:
        return "abnormal"
    if has_norm and not has_abn:
        return "normal"
    return None


def _find_side_tissue_labels(page) -> list[tuple[str, float, float, float]]:
    """Locate 'Normal Tissue' / 'Abnormal Tissue' titles to the left of tables.

    Real workbook PDFs place these titles in the left margin beside the grid
    (not as a caption above the table). Returns (kind, top, bottom, x0).
    """
    words = page.extract_words(use_text_flow=False) or []
    if not words:
        return []

    labels: list[tuple[str, float, float, float]] = []
    page_width = float(page.width or 612)
    left_max = page_width * 0.28  # side titles sit in the left margin

    # Horizontal phrase: "... Abnormal Tissue ..." / "... Normal Tissue ..."
    for i, w in enumerate(words):
        t = (w.get("text") or "").strip().lower()
        if t not in {"normal", "abnormal"}:
            continue
        if float(w.get("x0", 0)) > left_max:
            continue
        # Look ahead a few words for "Tissue" / "Tissues" on same line or stacked
        partner = None
        for j in range(i + 1, min(i + 6, len(words))):
            nxt = words[j]
            nt = (nxt.get("text") or "").strip().lower().rstrip("s")
            if nt != "tissue":
                continue
            # Same line (similar top) OR stacked below/above (similar x0)
            same_line = abs(float(nxt["top"]) - float(w["top"])) < 8
            stacked = abs(float(nxt["x0"]) - float(w["x0"])) < 18
            if same_line or stacked:
                partner = nxt
                break
        if partner is None:
            continue
        kind = "abnormal" if t == "abnormal" else "normal"
        top = min(float(w["top"]), float(partner["top"]))
        bottom = max(float(w.get("bottom", w["top"])), float(partner.get("bottom", partner["top"])))
        x0 = min(float(w["x0"]), float(partner["x0"]))
        labels.append((kind, top, bottom, x0))

    # Deduplicate near-identical labels
    deduped: list[tuple[str, float, float, float]] = []
    for lab in labels:
        if any(
            d[0] == lab[0] and abs(d[1] - lab[1]) < 12 and abs(d[3] - lab[3]) < 12
            for d in deduped
        ):
            continue
        deduped.append(lab)
    return deduped


def _kind_from_side_label(
    labels: list[tuple[str, float, float, float]],
    table_bbox: tuple[float, float, float, float] | None,
) -> str | None:
    """Pick the left-margin title whose vertical band overlaps this table."""
    if not labels or not table_bbox:
        return None
    _x0, y0, x1, y1 = table_bbox
    best: tuple[str, float] | None = None
    for kind, top, bottom, lx0 in labels:
        # Prefer labels to the left of the table
        if lx0 > x1:
            continue
        # Vertical overlap (or label sitting beside the top of the table)
        overlap = min(bottom, y1) - max(top, y0)
        near_top = abs(((top + bottom) / 2) - y0) < 40
        if overlap <= 0 and not near_top:
            # Expand: title often spans only the first few rows
            mid = (top + bottom) / 2
            if not (y0 - 30 <= mid <= y1 + 10):
                continue
            score = 1.0
        else:
            score = max(overlap, 1.0) + (100.0 if lx0 < _x0 else 0.0)
        if best is None or score > best[1]:
            best = (kind, score)
    return best[0] if best else None


def _kind_from_columns(cols: dict[str, int], rows: list[WorkbookRow]) -> str | None:
    """Infer Normal vs Abnormal from column layout when captions are missing."""
    # PB0669 Normal: Tissue | #pos / n | Comments (no Pathology)
    if "comments" in cols and "pathology" not in cols and (
        "pos" in cols or "ratio" in cols or "n" in cols
    ):
        return "normal"
    if "legend" in cols or any(r.legend_character for r in rows):
        return "abnormal"
    if "pathology" in cols:
        # Pathology cells that are diagnoses → Abnormal; all "Normal" → Normal Final Table
        paths = {(r.pathology or "").strip().lower() for r in rows if (r.pathology or "").strip()}
        paths.discard("")
        if paths and paths <= {"normal"}:
            return "normal"
        if paths:
            return "abnormal"
    return None


def _looks_like_pathology_not_comment(text: str) -> bool:
    """Compatibility wrapper — shared helper lives in counts."""
    return looks_like_pathology_not_comment(text)


def _recover_comments_from_text(
    text: str,
    rows: list[WorkbookRow],
    *,
    kind: str | None = None,
) -> None:
    """Fill blank Comments from page text lines that mention the tissue.

    Only recovers real staining comments (e.g. 'Somatotropic cells').
    Never pulls Abnormal pathology/count text into Normal Comments.
    Never treats tissue-name parentheticals (grey/white matter) as Comments.
    Never recovers Comments for 0/0 (not-included) tissues.
    Never matches a shorter tissue inside a longer one (Bladder ≠ Gallbladder).
    """
    if not text or not rows:
        return
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    tissue_names = [(r.tissue or "").strip() for r in rows if (r.tissue or "").strip()]

    for row in rows:
        # 0/0 = not included — leave Comments blank; do not invent notes
        if is_not_included(row.pos, row.n):
            row.comments = ""
            continue
        if (row.comments or "").strip():
            # Scrub mis-extracted pathology / tissue descriptors
            if kind == "normal" and (
                _looks_like_pathology_not_comment(row.comments)
                or looks_like_tissue_descriptor_not_comment(row.comments)
            ):
                row.comments = ""
            else:
                continue
        tissue = (row.tissue or "").strip()
        if not tissue or len(tissue) < 3:
            continue
        for line in lines:
            # Longest tissue name wins the line (Gallbladder before Bladder)
            owner = longest_tissue_for_line(line, tissue_names)
            if owner is None or owner.casefold() != tissue.casefold():
                continue
            m = tissue_line_match(line, tissue)
            if not m:
                continue
            rest = (m.group(1) or "").strip()
            # Skip lines that are clearly abnormal/pathology rows when filling Normal
            if kind == "normal" and re.search(
                r"\b(adenocarcinoma|carcinoma|adenoma|tumou?r|neoplasm|"
                r"legend|abnormal)\b",
                rest,
                flags=re.IGNORECASE,
            ):
                continue
            # Line is a longer tissue variant with parenthetical not in our name
            if rest.startswith("(") and "(" not in tissue:
                continue
            # Skip not-included (0/0) lines with no real comment
            if re.search(r"\b0\s*[/／⁄]\s*0\b", rest) or re.search(
                r"\b0\s+0\b", rest
            ):
                after_counts = re.sub(r"^[\d\s/／⁄]+", "", rest).strip()
                after_counts = re.sub(
                    r"^(normal|abnormal)\b\s*", "", after_counts, flags=re.I
                )
                if not after_counts or looks_like_tissue_descriptor_not_comment(
                    after_counts
                ):
                    continue
            rest = re.sub(
                r"^(normal|abnormal)\b\s*",
                "",
                rest,
                flags=re.IGNORECASE,
            )
            rest = re.sub(r"^[*†‡§¶]+\s*", "", rest)
            rest = re.sub(r"^[\d\s/／⁄]+", "", rest).strip()
            rest = re.sub(r"^[*†‡§¶]+\s*", "", rest)
            if not rest or _looks_like_count(rest):
                continue
            if rest.lower() in {"normal", "abnormal", "comments", "comment"}:
                continue
            if _looks_like_pathology_not_comment(rest):
                continue
            if looks_like_tissue_descriptor_not_comment(rest):
                continue
            # Do not steal another tissue's name as a "comment"
            if any(
                other.casefold() != tissue.casefold()
                and other.casefold() == rest.casefold()
                for other in tissue_names
            ):
                continue
            row.comments = scrub_comments(rest, tissue)
            if not row.comments:
                continue
            break

        row.comments = scrub_comments(row.comments, tissue)


def _split_text_by_final_table_kind(text: str) -> tuple[str, str]:
    """Split PDF text into Normal / Abnormal Final Table sections."""
    lines = text.splitlines()
    normal_lines: list[str] = []
    abnormal_lines: list[str] = []
    bucket: list[str] | None = None
    for line in lines:
        low = line.lower()
        if re.search(r"final\s+table\s*[–\-]?\s*abnormal", low) or re.search(
            r"\babnormal\s+tissue\s+staining\b", low
        ) or re.fullmatch(r"\s*abnormal\s+tissues?\s*", low):
            bucket = abnormal_lines
            continue
        if re.search(r"final\s+table\s*[–\-]?\s*normal", low) or re.search(
            r"\bnormal\s+tissue\s+staining\b", low
        ) or re.fullmatch(r"\s*normal\s+tissues?\s*", low):
            bucket = normal_lines
            continue
        # Side titles may appear alone on a line: "Normal Tissue" / "Abnormal Tissue"
        if re.search(r"^\s*abnormal\s+tissues?\b", low):
            bucket = abnormal_lines
            continue
        if re.search(r"^\s*normal\s+tissues?\b", low):
            bucket = normal_lines
            continue
        if bucket is not None:
            bucket.append(line)
    return "\n".join(normal_lines), "\n".join(abnormal_lines)


def _extract_tables_with_bbox(page) -> list[tuple[list, tuple[float, float, float, float] | None]]:
    """Return (table_rows, bbox) using find_tables when possible."""
    found = []
    try:
        found = page.find_tables() or []
    except Exception:  # noqa: BLE001
        found = []
    results: list[tuple[list, tuple[float, float, float, float] | None]] = []
    if found:
        for t in found:
            data = t.extract() or []
            if data:
                results.append((data, tuple(t.bbox)))  # type: ignore[arg-type]
        if results:
            return results
    # Fallback: extract_tables without bbox
    for table in _extract_tables(page):
        results.append((table, None))
    return results


def _extract_tables(page) -> list:
    """Try a couple of pdfplumber strategies — Comments are often lost with defaults."""
    tables = page.extract_tables() or []
    if tables:
        return tables
    alt = page.extract_tables(
        table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 5,
        }
    )
    return alt or []


def _tables_from_pdf(pdf) -> tuple[list[WorkbookRow], list[WorkbookRow]]:
    normal: list[WorkbookRow] = []
    abnormal: list[WorkbookRow] = []
    # Sticky kind from the most recent unambiguous Final Table heading
    active_kind: str | None = None

    for page in pdf.pages:
        page_text = page.extract_text() or ""
        page_kind = _classify_page_text(page_text)
        if page_kind:
            active_kind = page_kind

        side_labels = _find_side_tissue_labels(page)
        for table, bbox in _extract_tables_with_bbox(page):
            if not table or len(table) < 2:
                continue
            header_idx = None
            cols = None
            for i, row in enumerate(table[:5]):
                cols = _map_header([cell(c) for c in row])
                if cols:
                    header_idx = i
                    break
            if cols is None or header_idx is None:
                continue

            rows: list[WorkbookRow] = []
            in_legend = False
            for raw in table[header_idx + 1 :]:
                cells_list = list(raw or [])
                tissue_txt = ""
                path_txt = ""
                if "tissue" in cols and cols["tissue"] < len(cells_list):
                    tissue_txt = cell(cells_list[cols["tissue"]])
                if "pathology" in cols and cols["pathology"] < len(cells_list):
                    path_txt = cell(cells_list[cols["pathology"]])
                if is_legend_footer_row(tissue_txt, path_txt, in_legend=in_legend):
                    in_legend = True
                    continue
                parsed = _row_values(cells_list, cols)
                if parsed:
                    rows.append(parsed)
            if not rows:
                continue

            # Priority: left-margin title → column layout → sticky page heading
            local_kind = _kind_from_side_label(side_labels, bbox)
            if local_kind is None:
                local_kind = _kind_from_columns(cols, rows)
            if local_kind is None and active_kind in {"normal", "abnormal"}:
                local_kind = active_kind
            if local_kind is None:
                local_kind = "normal" if not normal else "abnormal"

            _recover_comments_from_text(page_text, rows, kind=local_kind)
            if local_kind == "normal":
                for r in rows:
                    if _looks_like_pathology_not_comment(r.comments):
                        r.comments = ""

            if local_kind == "abnormal":
                abnormal.extend(rows)
            else:
                normal.extend(rows)

    return normal, abnormal


def parse_workbook_pdf(source: PathLike, file_name: str | None = None) -> ParsedWorkbook:
    """Load Final Tables from a PCS Workbook PDF."""
    name = file_name
    if name is None and isinstance(source, (str, Path)):
        name = Path(source).name

    with pdfplumber.open(source) as pdf:
        normal, abnormal = _tables_from_pdf(pdf)
        full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    normal_text, abnormal_text = _split_text_by_final_table_kind(full_text)
    # Never scan Abnormal Final Table text when recovering Normal Comments
    _recover_comments_from_text(normal_text, normal, kind="normal")
    _recover_comments_from_text(abnormal_text, abnormal, kind="abnormal")
    for r in normal:
        if _looks_like_pathology_not_comment(r.comments):
            r.comments = ""

    if not normal and not abnormal:
        raise ValueError(
            "No Final Tables found in PDF. Expected pages/tables for "
            "'Final Table – Normal' and/or 'Final Table – Abnormal' "
            "(NCL-WI-000277 §3.7.8 attachment set)."
        )

    product = None
    for line in full_text.splitlines():
        low = line.lower()
        if "product name" in low and ":" in line:
            product = line.split(":", 1)[-1].strip() or None
            break
        if low.strip().startswith("product") and ":" in line and "claims" not in low:
            product = line.split(":", 1)[-1].strip() or None
            break

    return ParsedWorkbook(
        normal=normal,
        abnormal=abnormal,
        product_name=product,
        file_name=name,
    )
