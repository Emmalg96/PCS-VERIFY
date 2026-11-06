#!/usr/bin/env python3
"""
PCS Check — Streamlit app (PDF → Word + verify)

Windows (Command Prompt — NOT the Python >>> window):

  1. Put this whole project in e.g. C:\\Projects\\pcs-check
  2. Double-click RUN_STREAMLIT.bat
     OR in cmd:

       cd C:\\Projects\\pcs-check
       py -m pip install -r requirements.txt
       py -m streamlit run app.py --server.port 43123

  3. Open http://127.0.0.1:43123
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Always resolve the package next to this file (fixes "no module named pcs_verify")
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from pcs_verify.annotate import annotate_form_document
from pcs_verify.compare import CompareOptions, compare_tables
from pcs_verify.export_word import export_workbook_to_word
from pcs_verify.form import parse_form
from pcs_verify.pdf_workbook import parse_workbook_pdf
from pcs_verify.report import build_report, list_issue_lines
from pcs_verify.uprev import prepare_form_for_uprev
from pcs_verify.workbook import ParsedWorkbook, parse_workbook

st.set_page_config(
    page_title="PCS Check",
    page_icon="✓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.25rem; max-width: 1100px; }
      div[data-testid="stFileUploader"] {
        background: #f3f6f4; border-radius: 8px; padding: 0.5rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("PCS Check")
st.caption(
    "PDF → Word (Normal / Abnormal tissue tables) · Verify against Word · "
    "NCL-WI-000277 Rev 6 §3.7"
)


def load_workbook_upload(uploaded) -> ParsedWorkbook:
    suffix = Path(uploaded.name).suffix.lower()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / uploaded.name
        path.write_bytes(uploaded.getvalue())
        if suffix == ".pdf":
            return parse_workbook_pdf(path)
        if suffix in (".xlsx", ".xlsm"):
            return parse_workbook(path)
        raise ValueError("Upload a .pdf or .xlsx PCS Workbook.")


def load_form_upload(uploaded) -> tuple:
    """Return (ParsedForm, raw_bytes)."""
    data = uploaded.getvalue()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / uploaded.name
        path.write_bytes(data)
        return parse_form(path), data


def verification_passed(normal, abnormal, form) -> bool:
    """Fail when table values differ or Word still has combined #pos fractions."""
    layout_bad = any(
        "both numbers in #pos" in (w or "") for w in (form.warnings or [])
    )
    return (
        normal.passed
        and (abnormal.passed or abnormal.empty)
        and not layout_bad
    )


def show_verify_result(
    workbook,
    form,
    normal,
    abnormal,
    passed,
    *,
    form_bytes: bytes | None = None,
    form_name: str | None = None,
):
    if form.warnings:
        for w in form.warnings:
            if "both numbers in #pos" in (w or ""):
                st.warning(w)
            else:
                st.info(w)
    if form.count_format == "legacy":
        st.caption("Detected legacy count headers: **Pos / Neg** (mapped for comparison).")
    if passed:
        st.success("PASSED — Tables match.")
    else:
        st.error("FAILED — differences found.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Normal tissue match", normal.matched)
    m2.metric(
        "Normal tissue issues",
        normal.mismatched + normal.missing_in_form + normal.missing_in_workbook,
    )
    m3.metric("Abnormal tissue match", abnormal.matched)
    m4.metric(
        "Abnormal tissue issues",
        abnormal.mismatched + abnormal.missing_in_form + abnormal.missing_in_workbook,
    )
    issue_lines = list_issue_lines(normal, abnormal)
    if issue_lines:
        with st.expander(f"All issues ({len(issue_lines)})", expanded=True):
            for line in issue_lines:
                st.markdown(f"- {line}")
            st.caption(
                "The annotated Word file highlights cells and shows check notes "
                "under the values in the table (not in the Review pane). "
                "Tissues missing from Word are noted on the table header."
            )
    report = build_report(workbook, form, normal, abnormal, passed)
    st.download_button(
        "Download text report",
        report,
        file_name="pcs-verification-report.txt",
        mime="text/plain",
        key=f"txt-{form_name or 'report'}-{passed}",
    )
    if form_bytes is not None:
        try:
            annotated = annotate_form_document(
                form_bytes, normal, abnormal, overall_passed=passed
            )
            base = (form_name or "PCS_form").rsplit(".", 1)[0]
            if passed:
                st.download_button(
                    "Download Word (unchanged — everything matches)",
                    annotated,
                    file_name=f"{base}_PCS_CHECK_OK.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"ann-ok-{form_name or 'form'}",
                    help="No cell text or highlights added when everything matches.",
                )
                st.caption(
                    "Verification passed. The download is your Word file with no content changes."
                )
            else:
                st.download_button(
                    "Download annotated Word (highlights + in-cell notes)",
                    annotated,
                    file_name=f"{base}_PCS_CHECK_ANNOTATED.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"ann-{form_name or 'form'}",
                    help=(
                        "Amber = wrong value; orange = extra row. "
                        "Red notes appear under the cell value in the table."
                    ),
                )
                st.caption(
                    "Open the annotated Word file — incorrect cells are highlighted, "
                    "and a red **PCS Check** note sits under the value in that cell "
                    "(visible in the form, not the Review pane)."
                )
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not build annotated Word file: {exc}")
    with st.expander("Full report"):
        st.code(report)


mode = st.radio(
    "What do you want to do?",
    ["PDF → Word", "Verify against Word"],
    horizontal=True,
)

if mode == "PDF → Word":
    st.subheader("Convert approved Final Tables into Word")
    st.write(
        "Upload the approved PCS Workbook PDF (Sign Off + Final Tables), "
        "or Excel. Download Word **Normal tissue** / **Abnormal tissue** tables "
        "(PCS_PB0669-style columns). "
        "Abnormal legend characters are written as **superscript** in Pathology. "
        "Copied cells are **blue-shaded** with a review banner — a person must check "
        "them against the approved Final Tables before pasting into the controlled form."
    )
    src = st.file_uploader(
        "Approved PCS Workbook",
        type=["pdf", "xlsx", "xlsm"],
        key="p2w",
    )
    if st.button("Convert to Word (Normal / Abnormal tissue)", type="primary", disabled=src is None):
        try:
            workbook = load_workbook_upload(src)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "PCS_TABLES_3_4.docx"
                export_workbook_to_word(workbook, out)
                data = out.read_bytes()
            st.success(
                f"Ready — Normal {len(workbook.normal)} row(s), "
                f"Abnormal {len(workbook.abnormal)} row(s). "
                "Blue cells = copied from workbook — check them yourself before filing."
            )
            st.download_button(
                "Download Word tables (flagged for review)",
                data,
                file_name="PCS_TABLES_3_4_REVIEW.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                help=(
                    "Blue shading marks machine-copied values. "
                    "Compare every cell to the approved Final Tables, then remove shading."
                ),
            )
            st.caption(
                "This file is a **review aid**, not the controlled record. "
                "After SME/author check, clear the blue shading and banner before paste/filing."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

else:
    st.subheader("Check that Word Normal / Abnormal tissue tables match the approved workbook")
    st.write(
        "Matches tables by captions (**Normal tissue** / **Abnormal tissue**), "
        "not by table number. Works with **modern** forms (`#pos` / `n`) and **legacy** "
        "forms being uprevved (`Pos` / `Neg`)."
    )
    c1, c2 = st.columns(2)
    with c1:
        wb_file = st.file_uploader("Workbook (.pdf / .xlsx)", type=["pdf", "xlsx", "xlsm"], key="vwb")
    with c2:
        form_file = st.file_uploader("PCS form (.docx)", type=["docx"], key="vform")
    ignore_case = st.checkbox("Ignore letter case", value=False, key="vcase")
    merge_legend = st.checkbox("Expect legend in Word Pathology", value=True, key="vleg")
    neg_sum = st.checkbox(
        "Legacy only: Neg = negative count (n = Pos + Neg)",
        value=False,
        key="vneg",
        help="Leave unchecked if Neg was simply the old name for n (total tested).",
    )

    if st.button("Run verification", type="primary"):
        if not wb_file or not form_file:
            st.error("Upload both the workbook and the Word form.")
        else:
            try:
                options = CompareOptions(
                    ignore_case=ignore_case,
                    merge_legend_into_pathology=merge_legend,
                )
                workbook = load_workbook_upload(wb_file)
                parsed, form_bytes = load_form_upload(form_file)
                form = prepare_form_for_uprev(
                    parsed,
                    neg_means_negative_count=neg_sum,
                )
                normal = compare_tables("normal", workbook.normal, form.normal, options)
                abnormal = compare_tables(
                    "abnormal", workbook.abnormal, form.abnormal, options
                )
                passed = verification_passed(normal, abnormal, form)
                show_verify_result(
                    workbook,
                    form,
                    normal,
                    abnormal,
                    passed,
                    form_bytes=form_bytes,
                    form_name=form_file.name,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

st.divider()
st.caption(
    f"Project folder: `{ROOT}` · "
    "Samples: `public/samples/PCS_PB0669_Rev03.docx`, "
    "`PCS_FORM_LEGACY_POS_NEG.docx`"
)
