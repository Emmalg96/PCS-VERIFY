from __future__ import annotations

from datetime import datetime, timezone

from .compare import TableSummary
from .form import ParsedForm
from .workbook import ParsedWorkbook


def build_report(
    workbook: ParsedWorkbook,
    form: ParsedForm | None,
    normal: TableSummary,
    abnormal: TableSummary,
    overall_passed: bool,
) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "PCS VERIFICATION REPORT (Python)",
        "Excel Workbook Final Tables → Word PCS §4.1 / §4.2 (NCL-FRM-001659 → NCL-FRM-000146)",
        "=" * 72,
        f"Generated: {generated}",
        f"Result: {'PASSED' if overall_passed else 'FAILED'}",
        "",
        f"Workbook: {workbook.file_name or '(unnamed)'}",
    ]
    if workbook.product_name:
        lines.append(f"Product: {workbook.product_name}")
    lines.append(f"Form: {(form.file_name if form else None) or '(demo / unnamed)'}")
    lines.append(
        f"Workbook rows — Normal: {len(workbook.normal)}, Abnormal: {len(workbook.abnormal)}"
    )
    lines += [
        "",
        _block("Normal tissue", normal),
        "",
        _block("Abnormal tissue", abnormal),
    ]
    lines += ["", "Row details", "-" * 72]

    for summary in (normal, abnormal):
        lines.append("")
        lines.append("[Normal]" if summary.kind == "normal" else "[Abnormal]")
        for row in summary.results:
            lines.append(f"- {row.tissue or '(unknown)'}: {row.status.upper()}")
            for d in row.diffs:
                lines.append(
                    f'    {d.field}: workbook="{d.workbook}" form="{d.form}"'
                )

    lines += [
        "",
        "Rule basis: NCL-WI-000277 Rev 6 §3.7.6–3.7.7 — Final Tables from approved "
        "NCL-FRM-001659 into NCL-FRM-000146 §4.1/§4.2; Abnormal Legend Character "
        "(Col D) merged into Pathology; SME confirms superscript symbols.",
        "",
    ]
    return "\n".join(lines)


def _block(title: str, s: TableSummary) -> str:
    status = (
        "PASSED"
        if s.passed
        else ("N/A (empty)" if s.empty else "FAILED")
    )
    return "\n".join(
        [
            title,
            f"  Matched: {s.matched}",
            f"  Mismatches: {s.mismatched}",
            f"  Missing in Word: {s.missing_in_form}",
            f"  Extra in Word: {s.missing_in_workbook}",
            f"  Table result: {status}",
        ]
    )


def list_issue_lines(normal: TableSummary, abnormal: TableSummary) -> list[str]:
    """Human-readable list of every non-match (Normal / Abnormal tissue tables)."""
    lines: list[str] = []
    for summary in (normal, abnormal):
        label = "Normal tissue" if summary.kind == "normal" else "Abnormal tissue"
        for row in summary.results:
            if row.status == "match":
                continue
            if row.status == "missing-in-form":
                lines.append(
                    f"{label}: MISSING in Word — '{row.tissue}' is in the workbook/PDF"
                )
                continue
            if row.status == "missing-in-workbook":
                lines.append(
                    f"{label}: EXTRA in Word — '{row.tissue}' is not in the workbook/PDF"
                )
                continue
            if row.status == "mismatch":
                if not row.diffs:
                    lines.append(f"{label} / {row.tissue}: mismatch")
                    continue
                for d in row.diffs:
                    lines.append(
                        f'{label} / {row.tissue} — {d.field}: '
                        f'workbook/PDF="{d.workbook or "(blank)"}" · '
                        f'Word="{d.form or "(blank)"}"'
                    )
    return lines


def print_console_summary(normal: TableSummary, abnormal: TableSummary, overall_passed: bool) -> None:
    print()
    print("RESULT:", "PASSED ✓" if overall_passed else "FAILED ✗")
    print(
        f"  Normal  — match {normal.matched}, mismatch {normal.mismatched}, "
        f"missing {normal.missing_in_form}, extra {normal.missing_in_workbook}"
    )
    print(
        f"  Abnormal — match {abnormal.matched}, mismatch {abnormal.mismatched}, "
        f"missing {abnormal.missing_in_form}, extra {abnormal.missing_in_workbook}"
    )
    issues = [
        r
        for s in (normal, abnormal)
        for r in s.results
        if r.status != "match"
    ]
    if issues:
        print("\nIssues:")
        for r in issues[:30]:
            detail = "; ".join(
                f"{d.field}: '{d.workbook}' ≠ '{d.form}'" for d in r.diffs
            )
            print(f"  - [{r.kind}] {r.tissue}: {r.status}" + (f" ({detail})" if detail else ""))
        if len(issues) > 30:
            print(f"  … +{len(issues) - 30} more")
