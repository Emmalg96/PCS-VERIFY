# NCL-WI-000277 Rev 6 §3.7 ↔ PCS Check

Mapping of **Product Claims Summary Generation and Sustainment** (NCL-WI-000277 Rev 6) section **3.7 Generate Product Claims Summary (NCL-FRM-000146)** to what **PCS Check** covers today.

| WI step | Requirement (summary) | PCS Check |
|--------|------------------------|-----------|
| **3.7.1** | Workbook (NCL-FRM-001659) complete/reviewed/approved; design outputs approved; CP opens T: for approved PCS + workbook | **Out of scope** (process / controlled storage) |
| **3.7.2** | Complete PCS form per marker; follow guidance text | **Out of scope** (authoring) |
| **3.7.3** | Multiple product codes, same formulation → one PCS | **Out of scope** |
| **3.7.4** | Testing conditions in Table 1 | **Out of scope** (future check) |
| **3.7.5** | Section 4 tissue-component narrative; subcellular localisation from scoresheet | **Out of scope** (future / Copilot aide) |
| **3.7.6** | Final data tabs only from a **fully approved** workbook; insert Normal / Abnormal Final Tables into **§4.1** and **§4.2** | **Check 1 + PDF→Word** — extract from approved PDF/Excel and write Word §4.1/§4.2; does not prove approval status |
| **3.7.7** | Normal Final Table (§4.1) copied **exactly**. Abnormal Legend Character (Col D) **merged into Pathology**; legend in **superscript**; SME confirms | **PDF→Word** writes superscript legends and **blue-shades every copied cell** plus a review banner so a person can check the transfer. **Verify** checks character presence. SME still confirms visual superscript in the controlled form |
| **3.7.8** | PDF of approved workbook (Sign Off + Final Tables) attached as Appendix A | **PDF is the preferred source input** for PDF→Word; attaching to Appendix A remains a process step |
| **3.7.9–3.7.12** | SME/pathologist review; R&D or TO Manager approval; QA Design final sign-off; do not amend reviewer/approver count | **Out of scope** (exportable report may support review packets later) |
| **3.7.13** | Hardcopy initial rev to DDF | **Out of scope** |

## Controlled documents named in the WI

| Role | Document |
|------|----------|
| Work instruction | **NCL-WI-000277** Rev 6 |
| PCS Workbook | **NCL-FRM-001659** (Final Table – Normal / Final Table – Abnormal) |
| Product Claims Summary | **NCL-FRM-000146** (§4.1 Normal, §4.2 Abnormal) |

Form tables are matched by captions **Normal tissue** / **Abnormal tissue** (table numbers such as 3/4 are not relied on).

## Check 1 rule freeze (transcription)

Aligned to **3.7.6–3.7.7**:

1. Source of truth = workbook Final Tables (after approval — author responsibility).
2. §4.1 / Normal must match Final Table – Normal exactly (spelling/grammar/counts).
3. §4.2 / Abnormal Pathology must include workbook Pathology **plus** Legend Character when Col D was used.
4. Row identity by tissue; report missing, extra, and mismatched fields.
5. Superscript of legend symbols remains an **SME visual check** until a formatting check is added.

## Not claimed by the tool

PCS Check is a **verification gate**, not the system of record. It does not replace T: storage, DDF filing, sign-off workflows, or the requirement that Final Tables come only from a fully approved workbook.
