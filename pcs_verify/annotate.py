"""Annotate a PCS Word form: highlight incorrect cells and show notes in the table.

Notes appear under the cell value in the form (visible when reading the document).
Does not use the Word Review-pane Comments sidebar.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, Union

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from .compare import TableSummary
from .counts import looks_like_combined_fraction, layout_split_note, is_not_included
from .form import (
    _section_kind_from_text,
    classify_kind,
    header_map,
    is_legend_footer_row,
    is_tissue_table,
    kind_label,
    norm,
    row_from_cells,
)

PathLike = Union[str, Path, bytes, BinaryIO]

FILL_MISMATCH = "FFEB9C"  # amber — wrong value
FILL_EXTRA = "F8CBAD"  # orange — row not in workbook


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


FIELD_LABELS = {
    "tissue": "Tissue",
    "pathology": "Pathology",
    "legend": "Legend (in Pathology)",
    "pos": "#pos",
    "n": "n",
    "comments": "Comment",
}


def _display_value(value: str) -> str:
    v = (value or "").strip()
    return "blank" if not v else v


def _effectively_equal(workbook_value: str, form_value: str) -> bool:
    """True when both sides are the same after whitespace normalize (incl. both blank)."""
    a = " ".join((workbook_value or "").replace("\xa0", " ").split())
    b = " ".join((form_value or "").replace("\xa0", " ").split())
    return a == b


def _is_blank(value: str) -> bool:
    return not (value or "").strip()


def _diff_note(field: str, workbook_value: str, form_value: str) -> str | None:
    """Situation-specific note for this field only, or None when values already match."""
    if _effectively_equal(workbook_value, form_value):
        return None

    wb = (workbook_value or "").strip()
    form = (form_value or "").strip()
    wb_blank = _is_blank(wb)
    form_blank = _is_blank(form)

    if field == "comments":
        if wb_blank and not form_blank:
            return None
        if not wb_blank and form_blank:
            return f'Comment — workbook/PDF: "{wb}" · Word: blank.'
        return (
            f'Comment — workbook/PDF: "{wb}" · Word: "{form}". '
            "Comments do not match."
        )

    if field == "pos":
        return (
            f"#pos incorrect number — workbook/PDF: {wb or 'blank'} · "
            f"Word: {form or 'blank'}."
        )
    if field == "n":
        return (
            f"n incorrect number — workbook/PDF: {wb or 'blank'} · "
            f"Word: {form or 'blank'}."
        )

    if field == "pathology":
        if wb_blank and not form_blank:
            return (
                "Pathology — workbook/PDF: blank · Word: contains data "
                f'("{form}").'
            )
        if not wb_blank and form_blank:
            return f'Pathology — workbook/PDF: "{wb}" · Word: blank.'
        return (
            f'Pathology — workbook/PDF: "{wb}" · Word: "{form}". '
            "Pathology does not match."
        )

    if field == "legend":
        return (
            f"Legend — workbook/PDF has symbol '{wb}' · "
            f"Word Pathology: {_display_value(form)}."
        )

    if field == "tissue":
        return (
            f"Tissue — workbook/PDF: {_display_value(wb)} · "
            f"Word: {_display_value(form)}."
        )

    label = FIELD_LABELS.get(field, field)
    return (
        f"{label} — workbook/PDF: {_display_value(wb)} · "
        f"Word: {_display_value(form)}."
    )


def _counts_note(
    pos_wb: str | None,
    pos_form: str | None,
    n_wb: str | None,
    n_form: str | None,
) -> str | None:
    """One clear count note when #pos and/or n differ (e.g. Word 0/3 vs workbook 3/3)."""
    pos_diff = (
        pos_wb is not None
        and pos_form is not None
        and not _effectively_equal(pos_wb, pos_form)
    )
    n_diff = (
        n_wb is not None
        and n_form is not None
        and not _effectively_equal(n_wb, n_form)
    )
    if not pos_diff and not n_diff:
        return None

    if pos_wb is not None and n_wb is not None and pos_form is not None and n_form is not None:
        wb_frac = f"{(pos_wb or '').strip() or '?'}/{(n_wb or '').strip() or '?'}"
        form_frac = f"{(pos_form or '').strip() or '?'}/{(n_form or '').strip() or '?'}"
        if pos_diff and n_diff:
            return f"Counts incorrect — workbook/PDF: {wb_frac} · Word: {form_frac}."
        if pos_diff:
            return f"#pos incorrect — workbook/PDF: {wb_frac} · Word: {form_frac}."
        return f"n incorrect — workbook/PDF: {wb_frac} · Word: {form_frac}."

    if pos_diff:
        return _diff_note("pos", pos_wb or "", pos_form or "")
    return _diff_note("n", n_wb or "", n_form or "")


def _diff_finding_line(
    label: str, tissue: str, field: str, workbook_value: str, form_value: str
) -> str | None:
    note = _diff_note(field, workbook_value, form_value)
    if note is None:
        return None
    return f"{label} / {tissue} — {note}"


def _append_in_cell_note(cell, note: str) -> None:
    """Add a visible check note under the existing cell value (not a Review-pane comment)."""
    # Skip if this note was already written (re-annotate / shared header cells)
    marker = f"PCS Check: {note}"
    for p in cell.paragraphs:
        if marker in (p.text or ""):
            return
    p = cell.add_paragraph()
    run = p.add_run(f"⚠ PCS Check: {note}")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    run.italic = True


def _flag_cell(doc: Document, cell, note: str, fill_hex: str = FILL_MISMATCH) -> None:
    """Highlight the cell and show the check note in the cell (visible in the form)."""
    _ = doc  # kept for call-site compatibility
    _set_cell_fill(cell, fill_hex)
    _append_in_cell_note(cell, note)


def _field_to_columns(field: str, colmap: dict[str, int]) -> list[int]:
    if field == "tissue" and "tissue" in colmap:
        return [colmap["tissue"]]
    if field in {"pathology", "legend"} and "pathology" in colmap:
        return [colmap["pathology"]]
    if field == "pos" and "pos" in colmap:
        return [colmap["pos"]]
    if field == "n":
        cols = []
        if "n" in colmap:
            cols.append(colmap["n"])
        if "neg" in colmap:
            cols.append(colmap["neg"])
        return cols
    if field == "comments" and "comments" in colmap:
        return [colmap["comments"]]
    return []


def annotate_form_document(
    source: PathLike,
    normal: TableSummary,
    abnormal: TableSummary,
    *,
    overall_passed: bool,
) -> bytes:
    """Return a .docx with mismatches highlighted and notes shown in-cell."""
    if isinstance(source, (bytes, bytearray)):
        doc = Document(io.BytesIO(source))
    elif hasattr(source, "read"):
        doc = Document(source)  # type: ignore[arg-type]
    else:
        doc = Document(str(source))

    by_kind = {"normal": normal, "abnormal": abnormal}
    finding_lines: list[str] = []

    def index_results(summary: TableSummary) -> dict[str, list]:
        idx: dict[str, list] = {}
        for r in summary.results:
            key = norm(r.tissue).lower()
            idx.setdefault(key, []).append(r)
        return idx

    indexes = {k: index_results(v) for k, v in by_kind.items()}
    used_result_ids: set[int] = set()

    found_tables = 0
    preceding: list[str] = []
    active_section: str | None = None
    body = doc.element.body

    for child in list(body.iterchildren()):
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
            continue
        colmap = header_map(header_cells)
        if "tissue" not in colmap:
            continue

        parsed_rows = []
        data_row_indexes: list[int] = []
        in_legend = False
        for ri, row in enumerate(table.rows[1:], start=1):
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
            parsed = row_from_cells(cells, colmap)
            if not parsed:
                continue
            if not parsed.tissue.strip() and is_not_included(parsed.pos, parsed.n):
                continue
            parsed_rows.append(parsed)
            data_row_indexes.append(ri)

        if not parsed_rows:
            continue

        kind = classify_kind(
            preceding[-16:],
            parsed_rows,
            colmap,
            active_section=active_section,
        )
        idx = indexes[kind]
        label = kind_label(kind)

        for ri, parsed in zip(data_row_indexes, parsed_rows):
            key = norm(parsed.tissue).lower()
            candidates = idx.get(key, [])
            result = None
            for cand in candidates:
                if id(cand) in used_result_ids:
                    continue
                result = cand
                used_result_ids.add(id(cand))
                break

            row = table.rows[ri]

            raw_pos = ""
            raw_n = ""
            if "pos" in colmap and colmap["pos"] < len(row.cells):
                raw_pos = norm(row.cells[colmap["pos"]].paragraphs[0].text)
            if "n" in colmap and colmap["n"] < len(row.cells):
                raw_n = norm(row.cells[colmap["n"]].paragraphs[0].text)
            elif "neg" in colmap and colmap["neg"] < len(row.cells):
                raw_n = norm(row.cells[colmap["neg"]].paragraphs[0].text)

            layout_flagged = False
            if looks_like_combined_fraction(raw_pos, raw_n):
                layout_note = layout_split_note(raw_pos)
                layout_cols: list[int] = []
                layout_cols.extend(_field_to_columns("pos", colmap))
                layout_cols.extend(_field_to_columns("n", colmap))
                if "slash" in colmap:
                    layout_cols.append(colmap["slash"])
                for ci in layout_cols:
                    if ci < len(row.cells):
                        _flag_cell(doc, row.cells[ci], layout_note, FILL_MISMATCH)
                finding_lines.append(f"{label} / {parsed.tissue} — {layout_note}")
                layout_flagged = True

            if result is None or result.status == "match":
                continue

            if result.status == "missing-in-workbook":
                for cell in row.cells:
                    _set_cell_fill(cell, FILL_EXTRA)
                note = (
                    "Tissue: Word has this row, but it is not in the approved workbook/PDF."
                )
                _flag_cell(doc, row.cells[colmap["tissue"]], note, FILL_EXTRA)
                finding_lines.append(f"{label}: EXTRA row '{parsed.tissue}' — {note}")
                continue

            if result.status == "mismatch":
                by_field = {
                    d.field: d
                    for d in result.diffs
                    if not _effectively_equal(d.workbook, d.form)
                }

                pos_d = by_field.get("pos")
                n_d = by_field.get("n")
                if (pos_d or n_d) and not layout_flagged:
                    pos_wb = (
                        pos_d.workbook
                        if pos_d
                        else (result.workbook.pos if result.workbook else None)
                    )
                    pos_form = (
                        pos_d.form
                        if pos_d
                        else (result.form.pos if result.form else None)
                    )
                    n_wb = (
                        n_d.workbook
                        if n_d
                        else (result.workbook.n if result.workbook else None)
                    )
                    n_form = (
                        n_d.form
                        if n_d
                        else (result.form.n if result.form else None)
                    )
                    count_note = _counts_note(pos_wb, pos_form, n_wb, n_form)
                    if count_note:
                        count_cols: list[int] = []
                        if pos_d:
                            count_cols.extend(_field_to_columns("pos", colmap))
                        if n_d:
                            count_cols.extend(_field_to_columns("n", colmap))
                        if not count_cols and "tissue" in colmap:
                            count_cols = [colmap["tissue"]]
                        for ci in count_cols:
                            if ci < len(row.cells):
                                _flag_cell(doc, row.cells[ci], count_note, FILL_MISMATCH)
                        finding_lines.append(
                            f"{label} / {parsed.tissue} — {count_note}"
                        )

                for field, diff in by_field.items():
                    if field in {"pos", "n"}:
                        continue
                    note = _diff_note(field, diff.workbook, diff.form)
                    if note is None:
                        continue
                    cols = _field_to_columns(field, colmap) or (
                        [colmap["tissue"]] if "tissue" in colmap else []
                    )
                    for ci in cols:
                        if ci < len(row.cells):
                            _flag_cell(doc, row.cells[ci], note, FILL_MISMATCH)
                    line = _diff_finding_line(
                        label, parsed.tissue, field, diff.workbook, diff.form
                    )
                    if line:
                        finding_lines.append(line)

        preceding = []

    # Tissues in workbook but missing from Word — flag on each table's Tissue header
    header_by_kind: dict[str, object] = {}
    found_tables = 0
    preceding = []
    active_section = None
    for child in list(doc.element.body.iterchildren()):
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
            continue
        colmap = header_map(header_cells)
        if "tissue" not in colmap:
            continue
        parsed_rows = []
        for row in table.rows[1:]:
            cells = [norm(c.text) for c in row.cells]
            parsed = row_from_cells(cells, colmap)
            if parsed:
                parsed_rows.append(parsed)
        kind = classify_kind(
            preceding[-16:],
            parsed_rows,
            colmap,
            active_section=active_section,
        )
        header_by_kind[kind] = table.rows[0].cells[colmap["tissue"]]
        preceding = []

    for kind, summary in by_kind.items():
        label = kind_label(kind)
        missing = [r for r in summary.results if r.status == "missing-in-form"]
        for r in missing:
            note = (
                f"MISSING in Word — '{r.tissue}' is in the workbook/PDF and must be added."
            )
            finding_lines.append(f"{label}: {note}")
            header_cell = header_by_kind.get(kind)
            if header_cell is not None:
                _flag_cell(doc, header_cell, note, FILL_MISMATCH)

    _ = overall_passed
    _ = finding_lines

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
