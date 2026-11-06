#!/usr/bin/env python3
"""Build dist/pcs_checker_for_windows.zip — Python CLI + samples (no Streamlit)."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "pcs_checker_for_windows.zip"
PREFIX = "pcs-check"

# Paths relative to repo root to include (no Node / .git)
INCLUDE_FILES = [
    "requirements.txt",
    "README.md",
    "verify_pcs.py",
    "pcs_verify_standalone.py",
    "docs/PCS-TOOL-PROPOSAL.md",
    "docs/WI-000277-SECTION-3.7-MAPPING.md",
    "public/samples/PCS_PB0669_Rev03.docx",
]

INCLUDE_GLOBS = [
    "pcs_verify/*.py",
    "public/samples/*",
]

START_HERE = """PCS Check — Windows (command line)
=================================

This zip contains the Python **pcs_verify** package and sample files.

1. Unzip this folder to a path without spaces if possible, e.g.:
   C:\\Projects\\pcs-check

2. Open Command Prompt and run:

   cd C:\\Projects\\pcs-check
   py -m pip install -r requirements.txt

3. Verify a filled form against an approved workbook (examples):

   py -m pcs_verify public\\samples\\PCS_WORKBOOK_FINAL_TABLES.pdf public\\samples\\PCS_FORM_TABLES_MATCH.docx

   py verify_pcs.py path\\to\\workbook.pdf path\\to\\filled_form.docx

**Full browser UI (Next.js):** use the full repo with Node.js — see README.md ("Full web app").

Sample PDF: public\\samples\\PCS_WORKBOOK_FINAL_TABLES.pdf
"""


def main() -> None:
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
        zf.writestr(
            f"{PREFIX}/START_HERE_WINDOWS.txt".replace("\\", "/"),
            START_HERE,
        )
        for f in uniq:
            arc = Path(PREFIX) / f.relative_to(ROOT)
            zf.write(f, arcname=str(arc).replace("\\", "/"))

    print(f"Wrote {OUT} ({len(uniq)} files)")


if __name__ == "__main__":
    main()
