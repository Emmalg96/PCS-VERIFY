#!/usr/bin/env python3
"""
PCS Verification — single-file Excel -> Word checker

=== Windows setup (Command Prompt = cmd, NOT the Python >>> window) ===

  mkdir C:\\Projects
  cd C:\\Projects

  python -m pip install openpyxl python-docx

  python pcs_verify_standalone.py --demo match
  python pcs_verify_standalone.py --demo errors
  python pcs_verify_standalone.py your_workbook.xlsx your_filled_form.docx

Report is written to: pcs-verification-report.txt
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

try:
    from openpyxl import load_workbook
except ImportError:
    print("Missing openpyxl. Run: python -m pip install openpyxl python-docx", file=sys.stderr)
    raise SystemExit(2)

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    print("Missing python-docx. Run: python -m pip install openpyxl python-docx", file=sys.stderr)
    raise SystemExit(2)


def cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v).replace("\xa0", " ").strip()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


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
    normal: list
    abnormal: list
    product_name: str | None = None
    file_name: str | None = None


@dataclass
class FormRow:
    tissue: str
    pathology: str
    pos: str = ""
    n: str = ""
    comments: str = ""


@dataclass
class ParsedForm:
    normal: list
    abnormal: list
    file_name: str | None = None


@dataclass
class CompareOptions:
    ignore_case: bool = False
    ignore_whitespace: bool = True
    merge_legend_into_pathology: bool = True


@dataclass
class CellDiff:
    field: str
    workbook: str
    form: str


@dataclass
class RowResult:
    kind: str
    status: str
    tissue: str
    workbook: WorkbookRow | None = None
    form: FormRow | None = None
    expected_form_pathology: str = ""
    diffs: list = field(default_factory=list)


@dataclass
class TableSummary:
    kind: str
    results: list
    matched: int = 0
    mismatched: int = 0
    missing_in_form: int = 0
    missing_in_workbook: int = 0

    @property
    def passed(self) -> bool:
        return (
            self.mismatched == 0
            and self.missing_in_form == 0
            and self.missing_in_workbook == 0
            and self.matched > 0
        )

    @property
    def empty(self) -> bool:
        return (
            self.matched
            + self.mismatched
            + self.missing_in_form
            + self.missing_in_workbook
            == 0
        )


def parse_workbook(path: str | Path) -> ParsedWorkbook:
    path = Path(path)
    wb = load_workbook(path, data_only=True, read_only=True)
    product_name = None
    if "Sign Off Sheet" in wb.sheetnames:
        sign = wb["Sign Off Sheet"]
        for row in sign.iter_rows(min_row=5, max_row=5, min_col=2, max_col=2, values_only=True):
            product_name = cell(row[0]) if row else None
        if product_name == "XXXX (Ensure Clone is referenced)":
            product_name = None
    if "Final Table - Normal" not in wb.sheetnames and "Final Table - Abnormal" not in wb.sheetnames:
        raise ValueError('Missing "Final Table - Normal" / "Final Table - Abnormal" sheets.')

    normal = []
    if "Final Table - Normal" in wb.sheetnames:
        ws = wb["Final Table - Normal"]
        for r in range(2, (ws.max_row or 1) + 1):
            tissue = cell(ws.cell(r, 2).value)
            if not tissue:
                continue
            normal.append(
                WorkbookRow(
                    tissue,
                    cell(ws.cell(r, 3).value),
                    "",
                    cell(ws.cell(r, 4).value),
                    cell(ws.cell(r, 6).value),
                    cell(ws.cell(r, 7).value),
                )
            )
    abnormal = []
    if "Final Table - Abnormal" in wb.sheetnames:
        ws = wb["Final Table - Abnormal"]
        for r in range(3, (ws.max_row or 1) + 1):
            tissue = cell(ws.cell(r, 2).value)
            if tissue.lower() == "legend" or tissue.startswith("* Where comments"):
                break
            if not tissue:
                continue
            abnormal.append(
                WorkbookRow(
                    tissue,
                    cell(ws.cell(r, 3).value),
                    cell(ws.cell(r, 4).value),
                    cell(ws.cell(r, 5).value),
                    cell(ws.cell(r, 7).value),
                    cell(ws.cell(r, 8).value),
                )
            )
    return ParsedWorkbook(normal, abnormal, product_name, path.name)


def header_map(cells: list[str]) -> dict:
    mapping = {}
    for i, raw in enumerate(cells):
        h = norm(raw).lower()
        if not h:
            continue
        if "tissue" in h and "pathology" not in h:
            mapping.setdefault("tissue", i)
        elif h == "pathology" or h.startswith("pathology"):
            mapping.setdefault("pathology", i)
        elif "legend" in h:
            mapping.setdefault("legend", i)
        elif h in {"#pos", "pos"} or h.startswith("#pos"):
            mapping.setdefault("pos", i)
        elif h == "n" or h.startswith("n "):
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
    has_pos = any(h in {"#pos", "pos", "n"} or h.startswith("#pos") or "pos/" in h for h in headers)
    if "control tissue" in joined:
        return False
    return has_tissue and (has_pathology or has_pos)


def parse_form(path: str | Path) -> ParsedForm:
    path = Path(path)
    doc = Document(path)
    normal, abnormal = [], []
    found_tables = 0
    preceding = []
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
            preceding = []
            continue
        rows = []
        for row in table.rows[1:]:
            cells = [norm(c.text) for c in row.cells]
            def get(key):
                idx = colmap.get(key)
                return norm(cells[idx]) if idx is not None and idx < len(cells) else ""
            tissue, pathology = get("tissue"), get("pathology")
            if not tissue and not pathology:
                continue
            if tissue.lower() == "tissue":
                continue
            pos, n, comments, legend = get("pos"), get("n"), get("comments"), get("legend")
            if "ratio" in colmap:
                m = re.match(r"^(\d+)\s*/\s*(\d+)$", get("ratio"))
                if m:
                    pos, n = m.group(1), m.group(2)
            if legend and legend not in pathology:
                pathology = f"{pathology}{legend}" if pathology else legend
            rows.append(FormRow(tissue, pathology, pos, n, comments))
        if not rows:
            preceding = []
            continue
        text_paras = preceding[-16:]
        kind = "normal"
        for p in reversed(text_paras):
            t = (p or "").lower()
            if re.search(r"\babnormal\s+tissues?\b", t):
                kind = "abnormal"
                break
            if re.search(r"\bnormal\s+tissues?\b", t):
                kind = "normal"
                break
        else:
            joined = " ".join(text_paras).lower()
            if "table 4" in joined:
                kind = "abnormal"
            elif "table 3" in joined:
                kind = "normal"
            else:
                paths = [r.pathology.lower() for r in rows if r.pathology]
                kind = (
                    "normal"
                    if paths and all(p == "normal" or p.startswith("normal") for p in paths)
                    else "abnormal"
                )
        (normal if kind == "normal" else abnormal).extend(rows)
        preceding = []
    if not normal and not abnormal:
        raise ValueError(
            "No tissue tables found in Word doc (need Normal tissue / Abnormal tissue captions)."
        )
    return ParsedForm(normal, abnormal, path.name)


def normalize(raw: str, options: CompareOptions) -> str:
    v = (raw or "").replace("\xa0", " ")
    v = " ".join(v.split()) if options.ignore_whitespace else v.strip()
    return v.lower() if options.ignore_case else v


def eq(a: str, b: str, options: CompareOptions) -> bool:
    return normalize(a, options) == normalize(b, options)


def expected_form_pathology(row: WorkbookRow, options: CompareOptions) -> str:
    path, legend = row.pathology.strip(), row.legend_character.strip()
    if not options.merge_legend_into_pathology or not legend:
        return path
    if not path:
        return legend
    if path.endswith(legend) or legend in path:
        return path
    return f"{path}{legend}"


def pathology_includes_legend(form_pathology, workbook_pathology, legend, options) -> bool:
    fp, wp, lg = normalize(form_pathology, options), normalize(workbook_pathology, options), normalize(legend, options)
    if not lg:
        return eq(workbook_pathology, form_pathology, options)
    candidates = [
        normalize(f"{workbook_pathology}{legend}", options),
        normalize(f"{workbook_pathology} {legend}", options),
    ]
    if fp in candidates:
        return True
    return wp in fp and lg in fp


def compare_tables(kind, workbook_rows, form_rows, options=None) -> TableSummary:
    options = options or CompareOptions()
    results, used = [], set()
    excluded = set()

    def _split(pos, n):
        import re
        pos_s = " ".join((pos or "").replace("\xa0", " ").split())
        n_s = " ".join((n or "").replace("\xa0", " ").split())
        if n_s == "/":
            n_s = ""
        m = re.match(r"^(\d+)\s*[/／⁄]\s*(\d+)$", pos_s)
        if m and (not n_s or n_s == m.group(2)):
            return m.group(1), m.group(2)
        return pos_s, n_s

    def _not_included(pos, n):
        p, nn = _split(pos, n)
        return p == "0" and nn == "0"

    for wb in workbook_rows:
        if not wb.tissue.strip() and not wb.pathology.strip():
            continue
        if _not_included(wb.pos, wb.n):
            excluded.add(normalize(wb.tissue, options).lower())
            continue
        expected = expected_form_pathology(wb, options)
        match_index = next((i for i, fr in enumerate(form_rows) if i not in used and eq(wb.tissue, fr.tissue, options)), -1)
        if match_index < 0:
            results.append(RowResult(kind, "missing-in-form", wb.tissue, wb, None, expected, [CellDiff("tissue", wb.tissue, "")]))
            continue
        used.add(match_index)
        fr = form_rows[match_index]
        diffs = []
        if wb.legend_character and options.merge_legend_into_pathology:
            path_ok = pathology_includes_legend(fr.pathology, wb.pathology, wb.legend_character, options)
        else:
            path_ok = eq(expected, fr.pathology, options) or eq(wb.pathology, fr.pathology, options)
        if not path_ok:
            diffs.append(CellDiff("pathology", expected or wb.pathology, fr.pathology))
            if wb.legend_character and normalize(wb.legend_character, options) not in normalize(fr.pathology, options):
                diffs.append(CellDiff("legend", wb.legend_character, "(not found in form Pathology)"))
        wb_pos, wb_n = _split(wb.pos, wb.n)
        fr_pos, fr_n = _split(fr.pos, fr.n)
        if not eq(wb_pos, fr_pos, options):
            diffs.append(CellDiff("pos", wb_pos, fr_pos))
        if not eq(wb_n, fr_n, options):
            diffs.append(CellDiff("n", wb_n, fr_n))
        if kind == "normal":
            wb_c = wb.comments or ""
            # Never treat Abnormal pathology residue as a Normal Comment
            if re.search(
                r"\b(adenocarcinoma|carcinoma|adenoma|tumou?r|neoplasm)\b",
                wb_c,
                re.I,
            ) and re.search(r"\d+\s*/\s*\d+", wb_c):
                wb_c = ""
            if wb_c and not eq(wb_c, fr.comments, options):
                diffs.append(CellDiff("comments", wb_c, fr.comments))
        results.append(RowResult(kind, "match" if not diffs else "mismatch", wb.tissue, wb, fr, expected, diffs))
    for i, fr in enumerate(form_rows):
        if i in used or (not fr.tissue.strip() and not fr.pathology.strip()):
            continue
        if _not_included(fr.pos, fr.n):
            continue
        if normalize(fr.tissue, options).lower() in excluded:
            continue
        results.append(RowResult(kind, "missing-in-workbook", fr.tissue, None, fr, "", [CellDiff("tissue", "", fr.tissue)]))
    return TableSummary(
        kind,
        results,
        matched=sum(1 for r in results if r.status == "match"),
        mismatched=sum(1 for r in results if r.status == "mismatch"),
        missing_in_form=sum(1 for r in results if r.status == "missing-in-form"),
        missing_in_workbook=sum(1 for r in results if r.status == "missing-in-workbook"),
    )


DEMO_WB_N = [
    WorkbookRow("Cerebrum (grey matter tissue)", "Normal", "", "0", "3", ""),
    WorkbookRow("Tonsil", "Normal", "", "3", "3", "Lymphocytes positive"),
    WorkbookRow("Liver", "Normal", "", "0", "3", ""),
    WorkbookRow("Colon", "Normal", "", "2", "3", "Focal epithelial staining"),
]
DEMO_WB_A = [
    WorkbookRow("Colon", "Adenocarcinoma", "*", "5", "5", "Membranous staining"),
    WorkbookRow("Breast", "Invasive ductal carcinoma", "†", "4", "5", ""),
]
DEMO_FORM_N_MATCH = [FormRow(r.tissue, r.pathology, r.pos, r.n, r.comments) for r in DEMO_WB_N]
DEMO_FORM_A_MATCH = [FormRow(r.tissue, f"{r.pathology}{r.legend_character}", r.pos, r.n, r.comments) for r in DEMO_WB_A]
DEMO_FORM_N_ERR = [
    FormRow("Cerebrum (grey matter tissue)", "Normal", "0", "3", ""),
    FormRow("Tonsil", "Normal", "2", "3", "Lymphocytes positive"),
    FormRow("Liver", "Normal", "0", "3", ""),
]
DEMO_FORM_A_ERR = [
    FormRow("Colon", "Adenocarcinoma", "5", "5", "Membranous staining"),
    FormRow("Breast", "Invasive ductal carcinoma†", "4", "5", ""),
    FormRow("Lung", "Squamous cell carcinoma", "1", "1", ""),
]


def build_report(workbook, form, normal, abnormal, overall_passed) -> str:
    lines = [
        "PCS VERIFICATION REPORT",
        "Excel Final Tables -> Word Tables 3 & 4",
        "=" * 72,
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Result: {'PASSED' if overall_passed else 'FAILED'}",
        f"Workbook: {workbook.file_name}",
        f"Form: {form.file_name if form else ''}",
        "",
        f"Normal: match {normal.matched}, mismatch {normal.mismatched}, missing {normal.missing_in_form}, extra {normal.missing_in_workbook}",
        f"Abnormal: match {abnormal.matched}, mismatch {abnormal.mismatched}, missing {abnormal.missing_in_form}, extra {abnormal.missing_in_workbook}",
        "",
    ]
    for summary in (normal, abnormal):
        lines.append("[Normal]" if summary.kind == "normal" else "[Abnormal]")
        for row in summary.results:
            lines.append(f"- {row.tissue}: {row.status}")
            for d in row.diffs:
                lines.append(f'    {d.field}: workbook="{d.workbook}" form="{d.form}"')
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="PCS Excel->Word verification (standalone)")
    p.add_argument("workbook", nargs="?")
    p.add_argument("form", nargs="?")
    p.add_argument("--demo", choices=("match", "errors"))
    p.add_argument("-o", "--output", default="pcs-verification-report.txt")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--version", action="version", version=f"pcs_verify_standalone {__version__}")
    args = p.parse_args(argv)
    options = CompareOptions(ignore_case=args.ignore_case)

    if args.demo:
        workbook = ParsedWorkbook(DEMO_WB_N, DEMO_WB_A, "Demo Antibody", "demo.xlsx")
        if args.demo == "match":
            form = ParsedForm(DEMO_FORM_N_MATCH, DEMO_FORM_A_MATCH, "demo-match.docx")
        else:
            form = ParsedForm(DEMO_FORM_N_ERR, DEMO_FORM_A_ERR, "demo-errors.docx")
        print(f"Running demo: {args.demo}")
    else:
        if not args.workbook or not args.form:
            p.error("Provide workbook.xlsx and form.docx, or use --demo match|errors")
        print(f"Reading Excel: {args.workbook}")
        workbook = parse_workbook(args.workbook)
        print(f"  normal={len(workbook.normal)} abnormal={len(workbook.abnormal)}")
        print(f"Reading Word:  {args.form}")
        form = parse_form(args.form)
        print(f"  T3={len(form.normal)} T4={len(form.abnormal)}")

    normal = compare_tables("normal", workbook.normal, form.normal, options)
    abnormal = compare_tables("abnormal", workbook.abnormal, form.abnormal, options)
    passed = normal.passed and (abnormal.passed or abnormal.empty)
    print()
    print("RESULT:", "PASSED" if passed else "FAILED")
    print(f"  Normal:  match {normal.matched}, mismatch {normal.mismatched}, missing {normal.missing_in_form}, extra {normal.missing_in_workbook}")
    print(f"  Abnormal: match {abnormal.matched}, mismatch {abnormal.mismatched}, missing {abnormal.missing_in_form}, extra {abnormal.missing_in_workbook}")
    issues = [r for s in (normal, abnormal) for r in s.results if r.status != "match"]
    if issues:
        print("\nIssues:")
        for r in issues[:40]:
            detail = "; ".join(f"{d.field}: '{d.workbook}' != '{d.form}'" for d in r.diffs)
            print(f"  - [{r.kind}] {r.tissue}: {r.status}" + (f" ({detail})" if detail else ""))
    report = build_report(workbook, form, normal, abnormal, passed)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"\nReport written to: {Path(args.output).resolve()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
