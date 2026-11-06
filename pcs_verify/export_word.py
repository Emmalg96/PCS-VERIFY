"""Build a Product Claims Summary Word fragment matching NCL-FRM-000146 table layout.

Reference layout: PCS_PB0669_Rev03 (Table 3 Normal / Table 4 Abnormal).

Normal (Table 3):  Tissue | #pos | / | n | Comments
Abnormal (Table 4): Tissue | Pathology | #pos | / | n
  + Legend footer rows (symbol meaning), with legend chars in Pathology as superscript.

Copied data cells are shaded blue and the document carries a review banner so a
person (SME) can check the transfer against the approved Final Tables (WI §3.7.7).
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Union

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.table import Table

from .workbook import ParsedWorkbook, WorkbookRow
from .counts import split_pos_n, scrub_comments

PathLike = Union[str, Path]

# Light blue — machine-copied from workbook; person must check before filing
FILL_COPIED_REVIEW = "BDD7EE"


def _set_cell_fill(cell, fill_hex: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag == qn("w:shd"):
            tcPr.remove(child)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _flag_row_for_review(row) -> None:
    """Shade every cell in a data/legend row so a person can spot-check the copy."""
    for cell in row.cells:
        _set_cell_fill(cell, FILL_COPIED_REVIEW)


def _set_run_superscript(run, enabled: bool = True) -> None:
    run.font.superscript = enabled
    r = run._r
    rPr = r.get_or_add_rPr()
    vert = rPr.find(qn("w:vertAlign"))
    if enabled:
        if vert is None:
            vert = OxmlElement("w:vertAlign")
            rPr.append(vert)
        vert.set(qn("w:val"), "superscript")
    elif vert is not None:
        rPr.remove(vert)


def _bold_header_row(table: Table) -> None:
    for cell in table.rows[0].cells:
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True


def _write_pathology_with_legend(cell, pathology: str, legend: str) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    path = (pathology or "").strip()
    legend = (legend or "").strip()
    if legend and path.endswith(legend):
        path = path[: -len(legend)]
    if path:
        p.add_run(path)
    if legend:
        run = p.add_run(legend)
        _set_run_superscript(run, True)


def _add_normal_table(doc: Document, rows: list[WorkbookRow]) -> Table:
    """Table 3 layout: Tissue | #pos | / | n | Comments (no Pathology column)."""
    table = doc.add_table(rows=1 + len(rows), cols=5)
    table.style = "Table Grid"
    for i, h in enumerate(["Tissue", "#pos", "/", "n", "Comments"]):
        table.rows[0].cells[i].text = h
    _bold_header_row(table)
    for ri, row in enumerate(rows, start=1):
        pos, n = split_pos_n(row.pos, row.n)
        table.rows[ri].cells[0].text = row.tissue
        table.rows[ri].cells[1].text = pos
        table.rows[ri].cells[2].text = "/"
        table.rows[ri].cells[3].text = n
        table.rows[ri].cells[4].text = scrub_comments(row.comments, row.tissue)
        _flag_row_for_review(table.rows[ri])
    return table


def _legend_footer_entries(rows: list[WorkbookRow]) -> list[tuple[str, str]]:
    """Collect unique legend symbol → meaning pairs when comments hold meaning, else symbol only."""
    seen: dict[str, str] = {}
    for row in rows:
        sym = (row.legend_character or "").strip()
        if not sym:
            continue
        # Prefer explicit comment as meaning when present and not already used as staining note
        meaning = ""
        if row.comments and len(row.comments) < 80:
            # Don't treat long staining comments as legend meaning
            pass
        seen.setdefault(sym, meaning)
    return [(s, m) for s, m in seen.items()]


def _add_abnormal_table(doc: Document, rows: list[WorkbookRow]) -> Table:
    """Table 4 layout: Tissue | Pathology | #pos | / | n + Legend footer."""
    legends = _legend_footer_entries(rows)
    # PB0669 style: one "Legend" row then "*Plasma cells" style lines
    # Join wrapped meanings (PDF 2 lines → one Word legend line)
    from .form import join_legend_footer_lines

    legend_lines: list[str] = []
    for sym, meaning in legends:
        legend_lines.append(f"{sym}{meaning}" if meaning else sym)
    legend_lines = join_legend_footer_lines(legend_lines)

    # If workbook didn't supply meanings, still list symbols used (author fills meaning)
    if not legend_lines:
        syms = []
        for row in rows:
            s = (row.legend_character or "").strip()
            if s and s not in syms:
                syms.append(s)
        legend_lines = syms

    extra = (1 + len(legend_lines)) if legend_lines else 0
    table = doc.add_table(rows=1 + len(rows) + extra, cols=5)
    table.style = "Table Grid"
    for i, h in enumerate(["Tissue", "Pathology", "#pos", "/", "n"]):
        table.rows[0].cells[i].text = h
    _bold_header_row(table)

    for ri, row in enumerate(rows, start=1):
        pos, n = split_pos_n(row.pos, row.n)
        table.rows[ri].cells[0].text = row.tissue
        _write_pathology_with_legend(
            table.rows[ri].cells[1], row.pathology, row.legend_character
        )
        table.rows[ri].cells[2].text = pos
        table.rows[ri].cells[3].text = "/"
        table.rows[ri].cells[4].text = n
        _flag_row_for_review(table.rows[ri])

    if legend_lines:
        base = 1 + len(rows)
        table.rows[base].cells[0].text = "Legend"
        _flag_row_for_review(table.rows[base])
        for i, line in enumerate(legend_lines):
            # PB0669 footer style: "*Plasma cells" (symbol + meaning) in first column
            table.rows[base + 1 + i].cells[0].text = line
            _flag_row_for_review(table.rows[base + 1 + i])
    return table


def _add_copy_review_banner(doc: Document, workbook: ParsedWorkbook) -> None:
    """Tell the reader this file was machine-copied and must be checked by a person."""
    title = doc.add_paragraph()
    run = title.add_run("COPIED FROM WORKBOOK — check every cell yourself")
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    note = doc.add_paragraph()
    note_run = note.add_run(
        "Blue-shaded cells were copied from the approved Final Tables "
        f"({workbook.file_name or 'workbook'}). "
        "Before pasting into the controlled PCS form (NCL-FRM-000146), a person must "
        "compare Tissue, #pos, n, Comments, Pathology, and Legend superscripts against "
        "the source (NCL-WI-000277 §3.7.6–3.7.7). "
        "Remove this banner and the blue shading after review — do not file shaded copy "
        "as the controlled record."
    )
    note_run.italic = True

    checklist = doc.add_paragraph()
    checklist.add_run("Review checklist: ").bold = True
    checklist.add_run(
        "Normal tissue exact match · Abnormal Pathology includes legend as superscript · "
        "Comments match · no extra/missing tissues · then clear shading."
    )
    doc.add_paragraph("")


def build_pcs_tables_docx(
    workbook: ParsedWorkbook,
    *,
    product_name: str | None = None,
) -> Document:
    """Create Word §4.1 / §4.2 tables in PCS_PB0669-style layout."""
    doc = Document()
    _add_copy_review_banner(doc, workbook)

    title = doc.add_paragraph()
    run = title.add_run("Product Claims Summary — tissue staining tables")
    run.bold = True
    run.font.size = Pt(14)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    product = product_name or workbook.product_name or "Product"
    doc.add_paragraph(
        "Layout matches NCL-FRM-000146 Normal / Abnormal tissue tables "
        "(PCS_PB0669-style columns). "
        "Generated for paste into the controlled form after human review. "
        "Abnormal legend characters are superscripted in Pathology (NCL-WI-000277 §3.7.7)."
    )
    if workbook.file_name:
        doc.add_paragraph(f"Source: {workbook.file_name}")

    h = doc.add_paragraph()
    h.add_run("Normal Tissue Staining").bold = True
    doc.add_paragraph(f"Normal tissue staining for {product}")
    if workbook.normal:
        _add_normal_table(doc, workbook.normal)
    else:
        doc.add_paragraph("[No Normal Final Table rows found in source]")

    doc.add_paragraph("")
    h2 = doc.add_paragraph()
    h2.add_run("Abnormal Tissue Staining").bold = True
    doc.add_paragraph(f"Abnormal tissue staining for {product}")
    if workbook.abnormal:
        _add_abnormal_table(doc, workbook.abnormal)
    else:
        doc.add_paragraph("[No Abnormal Final Table rows found in source]")

    return doc


def export_workbook_to_word(
    workbook: ParsedWorkbook,
    destination: PathLike,
    *,
    product_name: str | None = None,
) -> Path:
    path = Path(destination)
    doc = build_pcs_tables_docx(workbook, product_name=product_name)
    doc.save(path)
    return path


def export_pdf_to_word(
    pdf_source: PathLike | BinaryIO,
    destination: PathLike,
    *,
    file_name: str | None = None,
) -> tuple[Path, ParsedWorkbook]:
    from .pdf_workbook import parse_workbook_pdf

    workbook = parse_workbook_pdf(pdf_source, file_name=file_name)
    path = export_workbook_to_word(workbook, destination)
    return path, workbook
