# PCS Transcription & Process Assistant — Tool Proposal

**Audience:** Product Claims Summary (PCS) authors, SMEs, QA  
**Documents in scope:** PCS Workbook (**NCL-FRM-001659**) · Product Claims Summary (**NCL-FRM-000146**) · WI (**NCL-WI-000277** Rev 6 §3.7)  
**Status:** Draft recommendation (aligned to WI Rev 6 §3.7 + current form/workbook templates)

---

## 1. Problem

PCS generation ends with a high-risk handoff: **approved Final Tables in the PCS Workbook must be pasted into the Product Claims Summary** (§4.1 Normal / §4.2 Abnormal), and from there feed IFU content.

NCL-WI-000277 Rev 6 §3.7.6–3.7.7 already states the requirement:

- Final data tabs only from a fully approved workbook (NCL-FRM-001659)  
- Insert Normal / Abnormal Final Tables into NCL-FRM-000146 §4.1 / §4.2  
- Normal Final Table copied exactly from the approved read-only workbook  
- If Legend Character (Col D) is used on Final Table – Abnormal, merge into Pathology (Col C) in §4.2; legend in superscript; SME confirms  

Today that check is largely **manual**. Errors (transposed counts, missing rows, dropped legend symbols, wording drift) are easy to miss and expensive late in review/approval.

Today that check is largely **manual**. Errors (transposed counts, missing rows, dropped legend symbols, wording drift) are easy to miss and expensive late in review/approval.

Authors are open to **an app, Copilot, or both**. Longer term there is interest in supporting **more of the PCS process**, not only the paste step.

---

## 2. Recommended tool (what it should be)

### One-line definition

**A controlled PCS quality assistant:** an application that validates critical handoffs in the PCS workflow—starting with Workbook → Product Claims Summary table transcription—and can grow into adjacent process checks without becoming a second document system of record.

### What it is

| It is | It is not |
|---|---|
| A **verification / gate** tool for defined PCS steps | A replacement for the Workbook or Form200 |
| Source-of-truth aware (Workbook Final Tables win for Tables 3/4) | A free-form chatbot as the only control |
| Explicit, repeatable rules (auditable) | A full LIMS / eQMS |
| Usable by authors before SME/QA review | A place to store controlled official copies long-term |

### Primary user jobs

1. **Author:** “Before I submit NCL-FRM-000146, prove my pasted tables match the approved workbook.”  
2. **SME / QA:** “Show me exactly what differs so I don’t re-proof every cell by eye.”  
3. **Process owner (later):** “Add the next high-error PCS check without inventing a new tool each time.”

---

## 3. Proposed product shape

### Core product: **PCS Check** (working name)

A small web app (or internal Office-add-in later) with **named checks**, each mapping to a real WI/form rule.

**Check 1 — Transcription (MVP, already prototyped)**  
- **Input A:** PCS Workbook `.xlsx` (reads `Final Table - Normal` / `Final Table - Abnormal`)  
- **Input B:** Product Claims Summary §4.1 / §4.2 (paste or `.docx` upload; Table 3/4 captions also accepted)  
- **Output:** Pass/fail + row-level diffs (tissue, pathology, `#pos`/`n`, comments, legend-in-pathology)  
- **Rule basis:** NCL-WI-000277 Rev 6 §3.7.6–3.7.7 (see `docs/WI-000277-SECTION-3.7-MAPPING.md`)  
- **Gap:** superscript formatting of legend symbols not automated yet — SME visual check remains  

**Optional companion: Copilot**  
- Use Copilot for drafting narrative sections (purpose/scope, IFU-style wording, references formatting tips)  
- **Do not** rely on Copilot alone for the transcription gate—rules must stay deterministic and reviewable  

### Experience principles

- **Document-native:** prefer upload/paste of real Form9182 / NCL-FRM-000146 artifacts over re-keying fields  
- **Diff-first:** every failure explains workbook value vs form value  
- **No silent “AI fixed it”:** suggest corrections; author applies them in the controlled document  
- **Demo modes:** known-good and known-bad examples for training  

---

## 4. Scope phases

### Phase 0 — Current prototype (done as a slice)

- Upload PCS Workbook; parse Final Tables  
- Paste Table 3 / Table 4 TSV; compare including abnormal legend merge  
- Demo mismatch / clean match  

### Phase 1 — Production-ready transcription gate (recommended next)

Make Check 1 usable in real authoring:

1. **Word table ingest** — accept pasted Word tables or `.docx` Table 3/4 extraction (reduce TSV friction)  
2. **Formatting note** — flag when structure diverges (extra columns, missing header, row order) without claiming full Word style fidelity  
3. **Exportable check report** — PDF/HTML summary for review packets (“transcription check run on &lt;file names&gt; / &lt;timestamp&gt;”)  
4. **Field freeze** — version the rule set against NCL-FRM-000146 Rev X / workbook template Rev Y  
5. **Access** — internal hosting; no persistence of product data by default (or optional short-lived session only)

**Success criteria (Phase 1)**  
- Authors can run a check in &lt;5 minutes on a real filled workbook + form  
- SME/QA accept the report as supporting evidence of table alignment  
- Zero “false pass” on known legend / `#pos`/`n` error cases in a qualification set  

### Phase 2 — Adjacent PCS process checks

Add only where errors or review time are high:

| Check | Source | Validates |
|---|---|---|
| **Final Table completeness** | Workbook | Empty abnormal rows, missing tissue, `#pos` &gt; `n`, blank required pathology |
| **Data checks consistency** | Workbook Data checks vs scoresheets | Totals / void / replicate sanity before sign-off |
| **Controls wording** | Form Table 2 vs SME guidance | Spelling/terminology destined for IFU |
| **References format** | Form §5 | Author/et al./journal pattern (lightweight lint) |
| **Workbook sign-off presence** | Sign Off Sheet | Required roles/dates present before form approval |

Still **not** owning D&D files, change requests, or T:\ controlled storage—only checks + reports.

### Phase 3 — Broader PCS process assistant (long run)

A single **PCS Process Hub** UI:

- Checklist of PCS lifecycle steps (planner → scoring → final tables → form → appendix → CR filing)  
- Links to WI/forms (e.g. NCL-WI-000277 where relevant)  
- Embedded **PCS Check** modules  
- Optional Copilot panel for “how do I fill section X?” using approved instructions only  
- Metrics: check pass rate, common failure types (for training)

---

## 5. Why an app as the backbone (with Copilot optional)

| Need | App / scripted check | Copilot-only |
|---|---|---|
| Same result every time for `#pos`/`n` / legend | Strong | Weak |
| Evidence for QA review | Exportable report | Chat transcript (messy) |
| Template/rev-controlled rules | Explicit | Drift risk |
| Drafting narrative / explaining WI | Weak | Strong |
| Quick ad-hoc question while editing | Medium | Strong |

**Recommendation:** **App = system of checks; Copilot = authoring aide.** Same team can use both; only the app is the gate for transcription.

---

## 6. What “good” looks like in 6–12 months

- Transcription mismatches are caught **before** SME/QA cycles, not during approval  
- New PCS authors are trained on a demo failure set in the tool  
- One or two additional checks (completeness / data checks) are live  
- Process owners can point to a short list of automated gates tied to form/WI text  
- Controlled documents remain in the existing QMS/path; the tool never becomes the record  

---

## 7. Out of scope (unless explicitly pulled in later)

- Replacing Form9182 scoring UI  
- Auto-writing the full Product Claims Summary  
- Auto-filing to controlled document locations  
- Changing IFU publishing systems  
- Unvalidated generative “rewrite my table” without human apply  

---

## 8. Immediate ask

Approve this framing:

1. **Tool identity:** PCS Check — verification gates for PCS handoffs  
2. **First production capability:** Workbook Final Tables ↔ NCL-FRM-000146 Tables 3/4  
3. **Next build increment:** Word-friendly ingest + exportable check report  
4. **Longer horizon:** expand check catalog along the PCS process; keep Copilot as optional assistant  

---

## 9. Open decisions for stakeholders

1. Must the check report be retained in the D&D / change request packet, or is author-only use enough?  
2. Preferred ingest for the form side: paste only, or full `.docx` upload?  
3. Who owns rule updates when NCL-FRM-000146 or the workbook template revises?  
4. Hosting: internal web app only, or also Excel/Word add-in later?  

---

*Draft derived from NCL-FRM-000146 Rev 7.1 instructions and the current PCS Workbook (Final Tables, legend handling, sign-off / data-check structure).*
