from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .compare import CompareOptions, compare_tables
from .demo import (
    DEMO_FORM_ABNORMAL_ERRORS,
    DEMO_FORM_ABNORMAL_MATCH,
    DEMO_FORM_NORMAL_ERRORS,
    DEMO_FORM_NORMAL_MATCH,
    DEMO_WORKBOOK_ABNORMAL,
    DEMO_WORKBOOK_NORMAL,
)
from .export_word import export_pdf_to_word, export_workbook_to_word
from .form import ParsedForm, parse_form
from .pdf_workbook import parse_workbook_pdf
from .report import build_report, print_console_summary
from .workbook import ParsedWorkbook, parse_workbook


def overall_pass(normal, abnormal) -> bool:
    abnormal_ok = abnormal.passed or abnormal.empty
    return normal.passed and abnormal_ok


def run_compare(
    workbook: ParsedWorkbook,
    form: ParsedForm,
    options: CompareOptions,
) -> tuple:
    normal = compare_tables("normal", workbook.normal, form.normal, options)
    abnormal = compare_tables("abnormal", workbook.abnormal, form.abnormal, options)
    return normal, abnormal, overall_pass(normal, abnormal)


def _load_source(path: Path) -> ParsedWorkbook:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        print(f"Reading PDF workbook: {path}")
        return parse_workbook_pdf(path)
    if suffix in (".xlsx", ".xlsm"):
        print(f"Reading Excel workbook: {path}")
        return parse_workbook(path)
    raise SystemExit(f"Unsupported workbook type: {path.suffix} (use .pdf or .xlsx)")


def cmd_pdf_to_word(args: argparse.Namespace) -> int:
    src = Path(args.source)
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        return 2
    out = Path(args.output or src.with_suffix("").name + "_PCS_TABLES_4.1_4.2.docx")
    if src.suffix.lower() == ".pdf":
        path, workbook = export_pdf_to_word(src, out, file_name=src.name)
    else:
        workbook = _load_source(src)
        path = export_workbook_to_word(workbook, out)
    print(f"Wrote Word §4.1 / §4.2 tables: {path.resolve()}")
    print(
        f"  Rows — Normal (§4.1): {len(workbook.normal)}, "
        f"Abnormal (§4.2): {len(workbook.abnormal)}"
    )
    print(
        "Legend characters are superscripted in Pathology (NCL-WI-000277 §3.7.7). "
        "Paste or merge into NCL-FRM-000146; SME still confirms superscripts."
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    options = CompareOptions(
        ignore_case=args.ignore_case,
        merge_legend_into_pathology=not args.no_legend_merge,
    )

    if args.demo:
        workbook = ParsedWorkbook(
            normal=DEMO_WORKBOOK_NORMAL,
            abnormal=DEMO_WORKBOOK_ABNORMAL,
            product_name="Demo Antibody (Clone A)",
            file_name="demo-workbook.xlsx",
        )
        if args.demo == "match":
            form = ParsedForm(
                normal=DEMO_FORM_NORMAL_MATCH,
                abnormal=DEMO_FORM_ABNORMAL_MATCH,
                file_name="demo-form-match.docx",
            )
        else:
            form = ParsedForm(
                normal=DEMO_FORM_NORMAL_ERRORS,
                abnormal=DEMO_FORM_ABNORMAL_ERRORS,
                file_name="demo-form-errors.docx",
            )
        print(f"Running demo: {args.demo}")
    else:
        if not args.workbook or not args.form:
            print(
                "Provide workbook.pdf|.xlsx and form.docx, or use --demo / pdf-to-word",
                file=sys.stderr,
            )
            return 2
        wb_path = Path(args.workbook)
        form_path = Path(args.form)
        if not wb_path.exists():
            print(f"Workbook not found: {wb_path}", file=sys.stderr)
            return 2
        if not form_path.exists():
            print(f"Form not found: {form_path}", file=sys.stderr)
            return 2
        workbook = _load_source(wb_path)
        print(
            f"  Final Tables — normal: {len(workbook.normal)}, abnormal: {len(workbook.abnormal)}"
        )
        print(f"Reading Word:  {form_path}")
        form = parse_form(form_path)
        print(f"  Tables — §4.1: {len(form.normal)}, §4.2: {len(form.abnormal)}")

    normal, abnormal, passed = run_compare(workbook, form, options)
    print_console_summary(normal, abnormal, passed)

    out = Path(args.output or "pcs-verification-report.txt")
    report = build_report(workbook, form, normal, abnormal, passed)
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {out.resolve()}")
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="pcs_verify",
        description=(
            "PCS Check — PDF/Excel Final Tables → Word NCL-FRM-000146 §4.1/§4.2 "
            "(NCL-WI-000277 Rev 6 §3.7)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"pcs_verify {__version__}")
    sub = parser.add_subparsers(dest="command")

    p2w = sub.add_parser(
        "pdf-to-word",
        help="Extract Final Tables from approved workbook PDF (or Excel) into a Word §4.1/§4.2 doc",
    )
    p2w.add_argument("source", help="Approved PCS Workbook .pdf (or .xlsx)")
    p2w.add_argument(
        "-o",
        "--output",
        help="Output .docx path (default: <source>_PCS_TABLES_4.1_4.2.docx)",
    )

    # Default verify interface (also works without subcommand for backward compat)
    parser.add_argument("workbook", nargs="?", help="PCS Workbook .pdf or .xlsx")
    parser.add_argument("form", nargs="?", help="Filled Product Claims Summary .docx")
    parser.add_argument("--demo", choices=("match", "errors"))
    parser.add_argument("-o", "--output", help="Verification report path")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--no-legend-merge", action="store_true")

    # Handle "pdf-to-word" as first arg before parse
    if argv and argv[0] == "pdf-to-word":
        args = parser.parse_args(argv)
        args.command = "pdf-to-word"
        # re-parse with subparser expectations
        p2w_args = p2w.parse_args(argv[1:])
        return cmd_pdf_to_word(p2w_args)

    args = parser.parse_args(argv)
    if args.command == "pdf-to-word":
        return cmd_pdf_to_word(args)
    return cmd_verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
