#!/usr/bin/env python3
"""Streamlit UI — PDF/Excel → Word §4.1/§4.2, plus optional verify.

  pip install -r requirements.txt
  streamlit run pcs_verify/ui_streamlit.py --server.port 43123
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from pcs_verify.compare import CompareOptions, compare_tables
from pcs_verify.export_word import export_workbook_to_word
from pcs_verify.form import parse_form
from pcs_verify.pdf_workbook import parse_workbook_pdf
from pcs_verify.report import build_report
from pcs_verify.workbook import parse_workbook

st.set_page_config(page_title="PCS Check — PDF → Word", layout="wide")
st.title("PCS Check")
st.caption(
    "Approved workbook PDF → Word §4.1 / §4.2 (superscript legends) · "
    "NCL-WI-000277 Rev 6 §3.7.6–3.7.8"
)

mode = st.radio("Mode", ["PDF → Word", "Verify PDF/Excel vs Word"], horizontal=True)

if mode == "PDF → Word":
    src = st.file_uploader("Approved PCS Workbook (.pdf or .xlsx)", type=["pdf", "xlsx"])
    if st.button("Convert to Word (§4.1 / §4.2)", type="primary") and src:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / src.name
            path.write_bytes(src.getvalue())
            try:
                if path.suffix.lower() == ".pdf":
                    workbook = parse_workbook_pdf(path)
                else:
                    workbook = parse_workbook(path)
                out = Path(tmp) / "PCS_TABLES_4.1_4.2.docx"
                export_workbook_to_word(workbook, out)
                st.success(
                    f"Ready — Normal {len(workbook.normal)}, Abnormal {len(workbook.abnormal)}. "
                    "Blue cells = copied from workbook — check them yourself before filing."
                )
                st.download_button(
                    "Download Word tables (flagged for review)",
                    out.read_bytes(),
                    file_name="PCS_TABLES_4.1_4.2_REVIEW.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                st.caption(
                    "Blue shading marks machine-copied values. Compare every cell to the "
                    "approved Final Tables, then remove shading before controlled filing."
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
else:
    col1, col2 = st.columns(2)
    with col1:
        wb_file = st.file_uploader("Workbook (.pdf / .xlsx)", type=["pdf", "xlsx"])
    with col2:
        form_file = st.file_uploader("Filled PCS form (.docx)", type=["docx"])
    ignore_case = st.checkbox("Ignore letter case", value=False)
    merge_legend = st.checkbox("Expect legend in Word Pathology", value=True)

    if st.button("Verify", type="primary"):
        if not wb_file or not form_file:
            st.error("Upload both files.")
            st.stop()
        options = CompareOptions(
            ignore_case=ignore_case,
            merge_legend_into_pathology=merge_legend,
        )
        with tempfile.TemporaryDirectory() as tmp:
            wb_path = Path(tmp) / wb_file.name
            form_path = Path(tmp) / form_file.name
            wb_path.write_bytes(wb_file.getvalue())
            form_path.write_bytes(form_file.getvalue())
            workbook = (
                parse_workbook_pdf(wb_path)
                if wb_path.suffix.lower() == ".pdf"
                else parse_workbook(wb_path)
            )
            form = parse_form(form_path)

        normal = compare_tables("normal", workbook.normal, form.normal, options)
        abnormal = compare_tables("abnormal", workbook.abnormal, form.abnormal, options)
        passed = normal.passed and (abnormal.passed or abnormal.empty)
        (st.success if passed else st.error)(
            "PASSED — tables match." if passed else "FAILED — differences found."
        )
        report = build_report(workbook, form, normal, abnormal, passed)
        st.download_button(
            "Download report",
            report,
            file_name="pcs-verification-report.txt",
            mime="text/plain",
        )
