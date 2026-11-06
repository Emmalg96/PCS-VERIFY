from __future__ import annotations

from dataclasses import dataclass, field

from .form import FormRow
from .workbook import WorkbookRow
from .counts import (
    split_pos_n,
    is_not_included,
    scrub_comments,
)


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
    diffs: list[CellDiff] = field(default_factory=list)


@dataclass
class TableSummary:
    kind: str
    results: list[RowResult]
    matched: int = 0
    mismatched: int = 0
    missing_in_form: int = 0
    missing_in_workbook: int = 0

    @property
    def passed(self) -> bool:
        checked = self.matched + self.mismatched + self.missing_in_form + self.missing_in_workbook
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


def normalize(raw: str, options: CompareOptions) -> str:
    v = (raw or "").replace("\xa0", " ")
    if options.ignore_whitespace:
        v = " ".join(v.split())
    else:
        v = v.strip()
    if options.ignore_case:
        v = v.lower()
    return v


def eq(a: str, b: str, options: CompareOptions) -> bool:
    return normalize(a, options) == normalize(b, options)


def expected_form_pathology(row: WorkbookRow, options: CompareOptions) -> str:
    path = row.pathology.strip()
    legend = row.legend_character.strip()
    if not options.merge_legend_into_pathology or not legend:
        return path
    if not path:
        return legend
    if path.endswith(legend) or legend in path:
        return path
    return f"{path}{legend}"


def pathology_includes_legend(
    form_pathology: str,
    workbook_pathology: str,
    legend: str,
    options: CompareOptions,
) -> bool:
    fp = normalize(form_pathology, options)
    wp = normalize(workbook_pathology, options)
    lg = normalize(legend, options)
    if not lg:
        return eq(workbook_pathology, form_pathology, options)
    candidates = [
        normalize(f"{workbook_pathology}{legend}", options),
        normalize(f"{workbook_pathology} {legend}", options),
        normalize(f"{legend}{workbook_pathology}", options),
    ]
    if fp in candidates:
        return True
    return wp in fp and lg in fp


def compare_tables(
    kind: str,
    workbook_rows: list[WorkbookRow],
    form_rows: list[FormRow],
    options: CompareOptions | None = None,
) -> TableSummary:
    options = options or CompareOptions()
    results: list[RowResult] = []
    used: set[int] = set()
    # Tissues with #pos=0 and n=0 are not included in the PCS — ignore them
    excluded_tissues: set[str] = set()

    for wb in workbook_rows:
        if not wb.tissue.strip() and not wb.pathology.strip():
            continue
        if is_not_included(wb.pos, wb.n):
            excluded_tissues.add(normalize(wb.tissue, options).lower())
            continue
        expected = expected_form_pathology(wb, options)
        match_index = next(
            (
                i
                for i, fr in enumerate(form_rows)
                if i not in used and eq(wb.tissue, fr.tissue, options)
            ),
            -1,
        )
        if match_index < 0:
            results.append(
                RowResult(
                    kind=kind,
                    status="missing-in-form",
                    tissue=wb.tissue,
                    workbook=wb,
                    expected_form_pathology=expected,
                    diffs=[CellDiff("tissue", wb.tissue, "")],
                )
            )
            continue

        used.add(match_index)
        fr = form_rows[match_index]
        diffs: list[CellDiff] = []

        if not eq(wb.tissue, fr.tissue, options):
            diffs.append(CellDiff("tissue", wb.tissue, fr.tissue))

        # Normal PCS Table 3 (PB0669-style) has no Pathology column — skip pathology compare
        if kind == "abnormal":
            if wb.legend_character and options.merge_legend_into_pathology:
                path_ok = pathology_includes_legend(
                    fr.pathology, wb.pathology, wb.legend_character, options
                )
            else:
                path_ok = eq(expected, fr.pathology, options) or eq(
                    wb.pathology, fr.pathology, options
                )

            if not path_ok:
                diffs.append(CellDiff("pathology", expected or wb.pathology, fr.pathology))
                if wb.legend_character and options.merge_legend_into_pathology:
                    if normalize(wb.legend_character, options) not in normalize(
                        fr.pathology, options
                    ):
                        diffs.append(
                            CellDiff(
                                "legend",
                                wb.legend_character,
                                "(not found in form Pathology)",
                            )
                        )

        # Workbook may store "0 / 1" in one field; Word correctly has #pos=0, n=1
        wb_pos, wb_n = split_pos_n(wb.pos, wb.n)
        fr_pos, fr_n = split_pos_n(fr.pos, fr.n)
        if not eq(wb_pos, fr_pos, options):
            diffs.append(CellDiff("pos", wb_pos, fr_pos))
        if not eq(wb_n, fr_n, options):
            diffs.append(CellDiff("n", wb_n, fr_n))
        # Comments on Normal only. Never treat tissue-name parentheticals
        # (grey/white matter) or Abnormal pathology residue as Comments.
        if kind == "normal":
            wb_comment = scrub_comments(wb.comments, wb.tissue)
            fr_comment = scrub_comments(fr.comments, fr.tissue)
            wb_c = normalize(wb_comment, options)
            fr_c = normalize(fr_comment, options)
            # Blank workbook/PDF comment + filled Word comment is OK; fail only when
            # the approved source has a non-blank comment that does not match Word.
            if wb_c and wb_c.lower() != fr_c.lower():
                diffs.append(CellDiff("comments", wb_comment, fr_comment))

        results.append(
            RowResult(
                kind=kind,
                status="match" if not diffs else "mismatch",
                tissue=wb.tissue,
                workbook=wb,
                form=fr,
                expected_form_pathology=expected,
                diffs=diffs,
            )
        )

    for i, fr in enumerate(form_rows):
        if i in used:
            continue
        if not fr.tissue.strip() and not fr.pathology.strip():
            continue
        # Not-included tissues (0/0) — do not flag as extra in Word
        if is_not_included(fr.pos, fr.n):
            continue
        if normalize(fr.tissue, options).lower() in excluded_tissues:
            continue
        results.append(
            RowResult(
                kind=kind,
                status="missing-in-workbook",
                tissue=fr.tissue,
                form=fr,
                diffs=[CellDiff("tissue", "", fr.tissue)],
            )
        )

    return TableSummary(
        kind=kind,
        results=results,
        matched=sum(1 for r in results if r.status == "match"),
        mismatched=sum(1 for r in results if r.status == "mismatch"),
        missing_in_form=sum(1 for r in results if r.status == "missing-in-form"),
        missing_in_workbook=sum(1 for r in results if r.status == "missing-in-workbook"),
    )
