from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from .counts import looks_like_combined_fraction, split_pos_n, is_not_included


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


@dataclass
class FormRow:
    tissue: str
    pathology: str
    pos: str = ""
    n: str = ""
    comments: str = ""


@dataclass
class ParsedForm:
    normal: list[FormRow]
    abnormal: list[FormRow]
    file_name: str | None = None
    warnings: list[str] | None = None
    # "modern" = #pos / n ; "legacy" = Pos / Neg columns detected
    count_format: str = "modern"


def header_map(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, raw in enumerate(cells):
        h = norm(raw).lower()
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
        # Legacy uprev columns: Pos | / | Neg  (parallel to modern #pos | / | n)
        elif h in {"neg", "negative", "#neg", "# negative"} or h.startswith("#neg"):
            mapping.setdefault("neg", i)
        elif h in {"#pos", "pos"} or h.startswith("#pos"):
            mapping.setdefault("pos", i)
        elif h == "n" or h.startswith("n ") or h == "#n":
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
        h in {"#pos", "pos", "n", "neg", "negative", "#neg"}
        or h.startswith("#pos")
        or h.startswith("#neg")
        or "pos/" in h
        or h == "#pos/n"
        for h in headers
    )
    if "control tissue" in joined:
        return False
    # Table 3 Normal may have Tissue + #pos/Pos + n/Neg + Comments (no Pathology)
    # Table 4 Abnormal has Tissue + Pathology + #pos/Pos + n/Neg
    return has_tissue and (has_pathology or has_pos)


# Legend footer symbols used under Abnormal tissue tables (PB0669 / Form9182)
LEGEND_SYMBOLS = ("*", "†", "‡", "§", "¶", "=", "※")


def is_legend_symbol_line(text: str) -> bool:
    """True when a cell/line starts a legend entry (* Reed-Sternberg cells, † Immune…)."""
    t = (text or "").strip()
    if not t:
        return False
    return t.startswith(LEGEND_SYMBOLS)


def is_legend_footer_row(
    tissue: str,
    pathology: str = "",
    *,
    in_legend: bool = False,
) -> bool:
    """True for Legend header, symbol lines, or continuation lines under Legend.

    PDF often wraps a long meaning across two lines:
      * Reed-Sternberg cells
      and immune cells
    Word may keep that as one cell. Continuations must not be parsed as tissues.
    Once the Legend section has started, every following row is footer (not data).
    """
    t = (tissue or "").strip()
    p = (pathology or "").strip()
    if not t and not p:
        return in_legend
    low = t.lower()
    if low == "legend":
        return True
    if is_legend_symbol_line(t):
        return True
    # Continuation of previous legend meaning (no new symbol)
    if in_legend:
        return True
    return False


def join_legend_footer_lines(lines: list[str]) -> list[str]:
    """Merge wrapped legend meanings into one entry per symbol.

    ['* Reed-Sternberg cells', 'and immune cells', '† Immune cells']
    → ['* Reed-Sternberg cells and immune cells', '† Immune cells']
    """
    out: list[str] = []
    for raw in lines:
        line = " ".join((raw or "").replace("\xa0", " ").split())
        if not line:
            continue
        if is_legend_symbol_line(line) or line.lower() == "legend":
            if line.lower() == "legend":
                continue
            out.append(line)
            continue
        if out:
            out[-1] = f"{out[-1]} {line}".strip()
        # else: stray text before any symbol — ignore
    return out


def row_from_cells(cells: list[str], colmap: dict[str, int]) -> FormRow | None:
    def get(key: str) -> str:
        idx = colmap.get(key)
        if idx is None or idx >= len(cells):
            return ""
        return norm(cells[idx])

    tissue = get("tissue")
    pathology = get("pathology")
    if not tissue and not pathology:
        return None
    if tissue.lower() == "tissue" and (
        not pathology or "pathology" in pathology.lower() or pathology.lower() == "#pos"
    ):
        return None
    if is_legend_footer_row(tissue, pathology):
        return None

    pos = get("pos")
    n = get("n")
    comments = get("comments")
    legend = get("legend")
    neg = get("neg")

    if "ratio" in colmap:
        ratio = get("ratio")
        m = re.match(r"^(\d+)\s*/\s*(\d+)$", ratio)
        if m:
            pos, n = m.group(1), m.group(2)

    # Legacy Pos | / | Neg → store Neg in n for comparison against workbook #pos / n
    if neg and not n:
        n = neg

    # People paste "0 / 3" into #pos and leave n blank — split for comparison
    pos, n = split_pos_n(pos, n)

    # Wrapped legend continuation (PDF 2nd line): "and immune cells" — not a tissue
    if tissue[:1].islower() and not pathology.strip() and not pos and not n and not comments:
        return None

    if legend and legend not in pathology:
        pathology = f"{pathology}{legend}" if pathology else legend

    return FormRow(tissue=tissue, pathology=pathology, pos=pos, n=n, comments=comments)


def row_has_combined_counts(cells: list[str], colmap: dict[str, int]) -> str | None:
    """If #pos holds a fraction and n is blank, return the raw #pos text; else None."""
    def get(key: str) -> str:
        idx = colmap.get(key)
        if idx is None or idx >= len(cells):
            return ""
        return norm(cells[idx])

    pos = get("pos")
    n = get("n") or get("neg")
    if looks_like_combined_fraction(pos, n):
        return pos
    return None


def _section_kind_from_text(text: str) -> str | None:
    """Return normal/abnormal from a section heading or table caption, else None."""
    t = norm(text).lower()
    if not t:
        return None
    # Prefer full section titles used in NCL-FRM-000146 (§4.1 / §4.2)
    if re.search(r"\babnormal\s+tissue\s+staining\b", t):
        return "abnormal"
    if re.search(r"\bnormal\s+tissue\s+staining\b", t):
        return "normal"
    # Shorter caption forms
    if re.search(r"\babnormal\s+tissues?\b", t):
        return "abnormal"
    if re.search(r"\bnormal\s+tissues?\b", t):
        return "normal"
    return None


def classify_kind(
    paragraphs_before: str | list[str],
    rows: list[FormRow],
    colmap: dict[str, int],
    *,
    active_section: str | None = None,
) -> str:
    """Decide normal vs abnormal.

    Priority:
    1. Sticky section from **Normal Tissue Staining** / **Abnormal Tissue Staining**
    2. Nearest caption above the table
    3. Column structure / weak fallbacks
    """
    if active_section in {"normal", "abnormal"}:
        return active_section

    if isinstance(paragraphs_before, str):
        paras = [p for p in re.split(r"[\n\r]+", paragraphs_before) if p.strip()]
        if len(paras) <= 1 and paragraphs_before.strip():
            paras = [paragraphs_before.strip()]
    else:
        paras = [p for p in paragraphs_before if (p or "").strip()]

    # Nearest caption above the table wins (walk newest → oldest)
    for p in reversed(paras[-16:]):
        kind = _section_kind_from_text(p)
        if kind:
            return kind

    # Column structure fallback (PB0669-style)
    if "pathology" in colmap:
        return "abnormal"
    if "comments" in colmap and "pathology" not in colmap:
        return "normal"

    joined = " ".join(paras[-8:]).lower()
    if re.search(r"table\s*4\b", joined):
        return "abnormal"
    if re.search(r"table\s*3\b", joined):
        return "normal"

    paths = [r.pathology.lower() for r in rows if r.pathology]
    if paths and all(p == "normal" or p.startswith("normal") for p in paths):
        return "normal"
    if paths:
        return "abnormal"
    return "normal"


def kind_label(kind: str) -> str:
    """User-facing table name (caption-based, not Table 3/4)."""
    return "Normal tissue" if kind == "normal" else "Abnormal tissue"


def parse_form(path: str | Path) -> ParsedForm:
    path = Path(path)
    doc = Document(path)
    normal: list[FormRow] = []
    abnormal: list[FormRow] = []
    warnings: list[str] = []
    found_tables = 0
    preceding: list[str] = []
    # Sticky §4.1 / §4.2 section — survives intervening non-tissue tables
    active_section: str | None = None
    saw_legacy_neg = False

    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            texts = [node.text for node in child.iter(qn("w:t")) if node.text]
            t = norm("".join(texts))
            if t:
                preceding.append(t)
                section = _section_kind_from_text(t)
                if section:
                    active_section = section
            continue
        if child.tag != qn("w:tbl"):
            continue

        table = doc.tables[found_tables]
        found_tables += 1
        if not table.rows:
            continue
        header_cells = [norm(c.text) for c in table.rows[0].cells]
        if not is_tissue_table(header_cells):
            # Do NOT clear active_section or caption history — headings sit above
            # decorative / other tables before the real tissue table.
            continue

        colmap = header_map(header_cells)
        if "tissue" not in colmap:
            warnings.append(f"Tissue table skipped (no Tissue column): {header_cells}")
            continue
        if "neg" in colmap:
            saw_legacy_neg = True

        rows: list[FormRow] = []
        combined_count = 0
        in_legend = False
        for row in table.rows[1:]:
            cells = [norm(c.text) for c in row.cells]
            tissue = cells[colmap["tissue"]] if colmap["tissue"] < len(cells) else ""
            pathology = (
                cells[colmap["pathology"]]
                if "pathology" in colmap and colmap["pathology"] < len(cells)
                else ""
            )
            if is_legend_footer_row(tissue, pathology, in_legend=in_legend):
                in_legend = True
                continue
            if row_has_combined_counts(cells, colmap):
                combined_count += 1
            parsed = row_from_cells(cells, colmap)
            if parsed:
                # Blank tissue with 0/0 filler rows — not real tissues
                if not parsed.tissue.strip() and is_not_included(parsed.pos, parsed.n):
                    continue
                rows.append(parsed)

        if combined_count:
            warnings.append(
                f"{combined_count} row(s) have both numbers in #pos (e.g. \"0 / 3\") "
                "with n blank. Put the first number in #pos, / in /, and the second in n."
            )

        if not rows:
            continue

        kind = classify_kind(
            preceding[-16:],
            rows,
            colmap,
            active_section=active_section,
        )
        if kind == "normal":
            normal.extend(rows)
        else:
            abnormal.extend(rows)
        # Reset caption buffer after consuming a tissue table; keep section until
        # the next Normal/Abnormal Tissue Staining heading.
        preceding = []

    if not normal and not abnormal:
        raise ValueError(
            "No tissue tables found (expected section headings "
            "'Normal Tissue Staining' / 'Abnormal Tissue Staining'). "
            "Supports modern (#pos / n) and legacy uprev (Pos / Neg) count columns."
        )

    if saw_legacy_neg:
        warnings.append(
            "Legacy Pos / Neg count columns detected (pre-Form9182 style). "
            "Neg is compared to workbook n unless you choose Pos+Neg → n."
        )

    return ParsedForm(
        normal=normal,
        abnormal=abnormal,
        file_name=path.name,
        warnings=warnings,
        count_format="legacy" if saw_legacy_neg else "modern",
    )
