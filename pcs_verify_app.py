#!/usr/bin/env python3
"""Backward-compatible entry: streamlit run pcs_verify_app.py → same as app.py """
from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "app.py"), run_name="__main__")
