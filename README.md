# PCS Verification

**Easiest on Windows: Streamlit app** (browser UI — PDF → Word + verify).

## Windows — Streamlit (recommended)

1. Put the **whole project** in e.g. `C:\Projects\pcs-check`  
   (must contain `app.py`, `requirements.txt`, and the `pcs_verify` folder).
2. **Double-click `RUN_STREAMLIT.bat`**  
   or in Command Prompt:

```bat
cd C:\Projects\pcs-check
py -m pip install -r requirements.txt
py -m streamlit run app.py --server.port 43123
```

3. Open **http://127.0.0.1:43123**

In the app:
- **PDF → Word** — upload approved workbook PDF → download §4.1 / §4.2 Word tables (superscript legends). Copied cells are **blue-shaded** with a review banner so a person can check the transfer before filing.
- **Verify against Word** — compare PDF/Excel to a filled NCL-FRM-000146 (supports modern `#pos`/`n` and legacy `Pos`/`Neg`)

**Important:** run commands from the project folder (where `requirements.txt` is), not from `C:\Users\...`.

---

## Command-line (optional)

```bash
pip install -r requirements.txt

# PDF → Word (§4.1 / §4.2 with superscript legends)
python3 -m pcs_verify pdf-to-word path/to/approved_workbook.pdf -o PCS_TABLES.docx

# Demo (no files needed)
python3 -m pcs_verify --demo errors
python3 -m pcs_verify --demo match

# Verify filled Word against PDF or Excel
python3 -m pcs_verify path/to/approved_workbook.pdf path/to/filled_PCS_FORM.docx
python3 -m pcs_verify path/to/PCS_WORKBOOK.xlsx path/to/filled_PCS_FORM.docx
```

Exit code `0` = passed, `1` = failed. A text report is written (default `pcs-verification-report.txt`).

#### Browser app on your PC (same Streamlit app)

```bat
cd C:\Projects\pcs-check
py -m streamlit run app.py --server.port 43123
```

Then open **http://127.0.0.1:43123**.

### What you need

| Already have | Needed |
|---|---|
| Python 3 | `pip install -r requirements.txt` (`openpyxl`, `python-docx`) |
| Node.js | **Not required** for the Python tool |

---

## Full web app (later, when Node.js is approved)

You do **not** download Next.js separately. Install **Node.js LTS**, then:

```bash
pip install -r requirements.txt
npm install          # installs Next.js automatically
npm run dev
```

Open http://127.0.0.1:43123 — upload Excel + Word in the browser.

---

## Internal company URL (Docker + GitHub)

To host this behind a **company-internal URL** using **GitHub** (build in Actions, image in GitHub Container Registry), see **`docs/INTERNAL-DEPLOYMENT.md`**.

**Run the published app with Docker:** `docker compose pull && docker compose up -d` then open **http://localhost:3000** (see `docker-compose.yml`).

---

## Sample files

- `public/samples/PCS_PB0669_Rev03.docx` — **real example** Product Claims Summary (Table 3 Normal / Table 4 Abnormal layout)
- `public/samples/PCS_WORKBOOK_FINAL_TABLES.pdf` — approved-style PDF (Sign Off + Final Tables)
- `public/samples/PCS_WORKBOOK.xlsx` — Excel Final Tables
- `public/samples/PCS_FORM_TABLES_MATCH.docx` — should **pass** against demo tables
- `public/samples/PCS_FORM_TABLES_ERRORS.docx` — should **fail**
- `public/samples/NCL-FRM-000146_Rev_7.1.docx` — blank template (no §4.1 / §4.2 tables yet)

**Note:** Use a *filled* Word form with Final Tables pasted into §4.1 / §4.2, not the empty template.

### Legacy Pos / Neg forms

Existing PCS forms being uprevved may use **Pos · / · Neg** instead of **#pos · / · n**.
Use **Verify against Word** with the approved workbook PDF as the source of truth
(optional checkbox if Neg means negative count rather than total `n`).

### Table layout (from PCS_PB0669_Rev03)

| Table | Columns |
|-------|---------|
| **Normal tissue** | Tissue · #pos · / · n · Comments *(no Pathology column)* |
| **Abnormal tissue** | Tissue · Pathology · #pos · / · n · Legend footer (`*…`) |

Tables are matched by **Normal tissue** / **Abnormal tissue** captions (not by table number).

Abnormal legend characters sit in the Pathology cell (superscript preferred per WI).

## Rule basis

See `docs/WI-000277-SECTION-3.7-MAPPING.md` for the full §3.7 step map (what Check 1 covers vs process/approval steps).
