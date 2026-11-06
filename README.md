# PCS Verification

Web app (**Next.js**) for PDF → Word (§4.1 / §4.2) and verify against NCL-FRM-000146. Python package **`pcs_verify`** powers parsing and conversion on the server.

## Full web app (recommended)

You need **Python 3** and **Node.js LTS** on the same machine (the API runs Python as a subprocess).

```bash
pip install -r requirements.txt
npm install
npm run dev
```

Open **http://127.0.0.1:43123** — upload files in the browser.

- **Production build:** `npm run build` then `npm run start` (same port).

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

---

## Internal company URL

- **Docker + GitHub (GHCR):** see **`docs/INTERNAL-DEPLOYMENT.md`** and `docker-compose.yml`.
- **Cursor Cloud / Pages (publish from Cursor):** see **`docs/CURSOR-PUBLISH.md`** — confirm your stack (Node + Python) is supported before enabling production use.

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
