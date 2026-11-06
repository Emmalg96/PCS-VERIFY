from __future__ import annotations

from .form import FormRow
from .workbook import WorkbookRow

DEMO_WORKBOOK_NORMAL = [
    WorkbookRow("Cerebrum (grey matter tissue)", "Normal", "", "0", "3", ""),
    WorkbookRow("Tonsil", "Normal", "", "3", "3", "Lymphocytes positive"),
    WorkbookRow("Liver", "Normal", "", "0", "3", ""),
    WorkbookRow("Colon", "Normal", "", "2", "3", "Focal epithelial staining"),
]

DEMO_WORKBOOK_ABNORMAL = [
    WorkbookRow("Colon", "Adenocarcinoma", "*", "5", "5", "Membranous staining"),
    WorkbookRow("Breast", "Invasive ductal carcinoma", "†", "4", "5", ""),
]

DEMO_FORM_NORMAL_MATCH = [
    FormRow(r.tissue, r.pathology, r.pos, r.n, r.comments) for r in DEMO_WORKBOOK_NORMAL
]

DEMO_FORM_ABNORMAL_MATCH = [
    FormRow(r.tissue, f"{r.pathology}{r.legend_character}", r.pos, r.n, r.comments)
    for r in DEMO_WORKBOOK_ABNORMAL
]

DEMO_FORM_NORMAL_ERRORS = [
    FormRow("Cerebrum (grey matter tissue)", "Normal", "0", "3", ""),
    FormRow("Tonsil", "Normal", "2", "3", "Lymphocytes positive"),
    FormRow("Liver", "Normal", "0", "3", ""),
]

DEMO_FORM_ABNORMAL_ERRORS = [
    FormRow("Colon", "Adenocarcinoma", "5", "5", "Membranous staining"),
    FormRow("Breast", "Invasive ductal carcinoma†", "4", "5", ""),
    FormRow("Lung", "Squamous cell carcinoma", "1", "1", ""),
]
