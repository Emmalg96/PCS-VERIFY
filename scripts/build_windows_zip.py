#!/usr/bin/env python3
"""Build dist/pcs_checker_for_windows.zip — one download for Windows + Streamlit."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "pcs_checker_for_windows.zip"
PREFIX = "pcs-check"

# Paths relative to repo root to include (no Node / .git)
INCLUDE_FILES = [
    "app.py",
    "RUN_STREAMLIT.bat",
    "requirements.txt",
    "README.md",
    "verify_pcs.py",
    "pcs_verify_app.py",
    "pcs_verify_standalone.py",
    "START_HERE_WINDOWS.txt",
    "docs/PCS-TOOL-PROPOSAL.md",
    "docs/WI-000277-SECTION-3.7-MAPPING.md",
    "public/samples/PCS_PB0669_Rev03.docx",
]

INCLUDE_GLOBS = [
    "pcs_verify/*.py",
    "public/samples/*",
]


def main() -> None:
    start = ROOT / "START_HERE_WINDOWS.txt"
    start.write_text(
        """PCS Check — Windows (Streamlit)
================================

1. Unzip this folder to:
   C:\\Projects\\pcs-check

2. Double-click RUN_STREAMLIT.bat
   OR open Command Prompt and run:

   cd C:\\Projects\\pcs-check
   py -m pip install -r requirements.txt
   py -m streamlit run app.py --server.port 43123

3. Open http://127.0.0.1:43123 in Chrome or Edge

In the app:
  - PDF → Word
  - Verify against Word

Do NOT save individual .url shortcuts from the browser — use this zip.

Sample PDF: public\\samples\\PCS_WORKBOOK_FINAL_TABLES.pdf
""",
        encoding="utf-8",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for rel in INCLUDE_FILES:
        p = ROOT / rel
        if p.is_file():
            files.append(p)
    for pattern in INCLUDE_GLOBS:
        files.extend(ROOT.glob(pattern))

    # de-dupe
    uniq = sorted({f.resolve() for f in files if f.is_file()})

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in uniq:
            arc = Path(PREFIX) / f.relative_to(ROOT)
            zf.write(f, arcname=str(arc).replace("\\", "/"))

    print(f"Wrote {OUT} ({len(uniq)} files)")


if __name__ == "__main__":
    main()
