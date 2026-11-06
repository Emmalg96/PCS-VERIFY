/** Row from PCS Workbook Final Table - Normal / Abnormal (Form9182). */
export type WorkbookRow = {
  tissue: string;
  pathology: string;
  /** Abnormal table only — merged into Pathology when pasting into PCS Form. */
  legendCharacter: string;
  pos: string;
  n: string;
  comments: string;
};

export type TableKind = "normal" | "abnormal";

export type ParsedWorkbookTables = {
  normal: WorkbookRow[];
  abnormal: WorkbookRow[];
  productName?: string;
  fileName?: string;
};

export type FormRow = {
  tissue: string;
  pathology: string;
  pos: string;
  n: string;
  comments: string;
};

export type CellDiff = {
  field: "tissue" | "pathology" | "pos" | "n" | "comments" | "legend";
  workbook: string;
  form: string;
};

export type RowCompareStatus =
  | "match"
  | "mismatch"
  | "missing-in-form"
  | "missing-in-workbook";

export type RowCompareResult = {
  key: string;
  kind: TableKind;
  status: RowCompareStatus;
  workbook?: WorkbookRow;
  form?: FormRow;
  /** Expected pathology in the form after legend merge (abnormal). */
  expectedFormPathology?: string;
  diffs: CellDiff[];
};

export type TableCompareSummary = {
  kind: TableKind;
  results: RowCompareResult[];
  matched: number;
  mismatched: number;
  missingInForm: number;
  missingInWorkbook: number;
  passed: boolean;
};

export type CompareOptions = {
  ignoreCase: boolean;
  ignoreWhitespace: boolean;
  /** For abnormal rows: expect legend character inside form Pathology (per NCL-FRM-000146). */
  mergeLegendIntoPathology: boolean;
};

export const DEFAULT_COMPARE_OPTIONS: CompareOptions = {
  ignoreCase: false,
  ignoreWhitespace: true,
  mergeLegendIntoPathology: true,
};

export function cellText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  // ExcelJS formula cells: { formula, result }
  if (typeof value === "object") {
    const obj = value as { result?: unknown; text?: string; richText?: { text: string }[] };
    if ("result" in obj && obj.result != null) {
      return cellText(obj.result);
    }
    if (Array.isArray(obj.richText)) {
      return obj.richText.map((t) => t.text).join("");
    }
    if (typeof obj.text === "string") return obj.text;
  }
  return String(value).replace(/\u00a0/g, " ").trim();
}

export function normalizeText(raw: string, options: CompareOptions): string {
  let v = raw ?? "";
  v = v.replace(/\u00a0/g, " ");
  if (options.ignoreWhitespace) {
    v = v.replace(/\s+/g, " ").trim();
  } else {
    v = v.trim();
  }
  if (options.ignoreCase) v = v.toLowerCase();
  return v;
}

export function expectedFormPathology(
  row: WorkbookRow,
  options: CompareOptions,
): string {
  const path = row.pathology.trim();
  const legend = row.legendCharacter.trim();
  if (!options.mergeLegendIntoPathology || !legend) return path;
  if (!path) return legend;
  // Common paste patterns: "Adenocarcinoma*" or "Adenocarcinoma *"
  if (path.endsWith(legend) || path.includes(legend)) return path;
  return `${path}${legend}`;
}

function rowKey(tissue: string, pathology: string): string {
  return `${tissue.trim().toLowerCase()}||${pathology.trim().toLowerCase()}`;
}

export function workbookRowKey(row: WorkbookRow): string {
  return rowKey(row.tissue, row.pathology);
}

export function formRowKey(row: FormRow): string {
  return rowKey(row.tissue, row.pathology);
}

/** Split "0 / 3" pasted into #pos when n is blank → { pos: "0", n: "3" }. */
export function splitPosN(pos: string, n: string = ""): { pos: string; n: string } {
  const posS = (pos ?? "").replace(/\u00a0/g, " ").trim().replace(/\s+/g, " ");
  let nS = (n ?? "").replace(/\u00a0/g, " ").trim().replace(/\s+/g, " ");
  if (nS === "/") nS = "";
  const m = posS.match(/^(\d+)\s*[/／⁄]\s*(\d+)$/);
  if (m) {
    const num = m[1];
    const den = m[2];
    if (!nS || nS === den) return { pos: num, n: den };
    return { pos: posS, n: nS };
  }
  return { pos: posS, n: nS };
}

/** #pos=0 and n=0 means this tissue type is not included in the PCS workbook. */
export function isNotIncluded(pos: string, n: string = ""): boolean {
  const { pos: p, n: nn } = splitPosN(pos, n);
  return p === "0" && nn === "0";
}

/**
 * Parse tab/CSV pasted text from Word PCS Form tables (Table 3 / Table 4).
 *
 * Table 3 Normal (PCS_PB0669): Tissue | #pos | / | n | Comments
 * Table 4 Abnormal:            Tissue | Pathology | #pos | / | n
 */
export function parseFormTablePaste(text: string): FormRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.replace(/^\s+/, ""))
    .filter((l) => l.trim().length > 0);

  if (lines.length === 0) return [];

  const rows: FormRow[] = [];
  for (const line of lines) {
    const cols = splitLine(line);
    if (cols.length === 0) continue;
    if (looksLikeHeader(cols)) continue;

    let tissue = "";
    let pathology = "";
    let pos = "";
    let n = "";
    let comments = "";

    // Tissue | #pos | / | n | Comments  (Normal — no Pathology)
    if (cols.length >= 5 && cols[2] === "/" && !looksLikePathologyToken(cols[1])) {
      tissue = cols[0];
      pos = cols[1];
      n = cols[3];
      comments = cols.slice(4).join(" ");
    } else if (cols.length >= 6 && cols[3] === "/") {
      // Tissue | Pathology | #pos | / | n [| Comments]
      tissue = cols[0];
      pathology = cols[1];
      pos = cols[2];
      n = cols[4];
      comments = cols.slice(5).join(" ");
    } else if (cols.length >= 5) {
      [tissue, pathology, pos, n, comments] = [
        cols[0],
        cols[1],
        cols[2],
        cols[3],
        cols.slice(4).join(" "),
      ];
      if (cols[3] === "/" && cols.length >= 6) {
        pos = cols[2];
        n = cols[4];
        comments = cols.slice(5).join(" ");
      }
    } else if (cols.length === 4) {
      tissue = cols[0];
      pathology = cols[1];
      const ratio = cols[2];
      comments = cols[3];
      const m = ratio.match(/^(\d+)\s*\/\s*(\d+)$/);
      if (m) {
        pos = m[1];
        n = m[2];
      } else {
        pos = ratio;
      }
    } else if (cols.length === 3) {
      tissue = cols[0];
      pathology = cols[1];
      const ratio = cols[2];
      const m = ratio.match(/^(\d+)\s*\/\s*(\d+)$/);
      if (m) {
        pos = m[1];
        n = m[2];
      }
    } else {
      continue;
    }

    const t = tissue.trim();
    if (!t && !pathology.trim()) continue;
    if (t.toLowerCase() === "legend") continue;
    if (/^[*†‡§¶]/.test(t) && !pathology.trim()) continue;

    const split = splitPosN(cellText(pos), cellText(n));
    rows.push({
      tissue: t,
      pathology: pathology.trim(),
      pos: split.pos,
      n: split.n,
      comments: comments.trim(),
    });
  }
  return rows;
}

function looksLikePathologyToken(value: string): boolean {
  const v = value.trim().toLowerCase();
  if (!v) return false;
  if (/^\d+$/.test(v)) return false; // #pos
  if (v === "/" || v === "n" || v.startsWith("#pos")) return false;
  return true;
}

function splitLine(line: string): string[] {
  if (line.includes("\t")) return line.split("\t").map((c) => c.trim());
  // CSV-ish
  if (line.includes(",")) {
    return line.split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
  }
  // multiple spaces
  return line.split(/\s{2,}/).map((c) => c.trim());
}

function looksLikeHeader(cols: string[]): boolean {
  const joined = cols.join(" ").toLowerCase();
  return (
    joined.includes("tissue") &&
    (joined.includes("pathology") || joined.includes("#pos") || joined.includes("pos"))
  );
}

export function compareTables(
  kind: TableKind,
  workbookRows: WorkbookRow[],
  formRows: FormRow[],
  options: CompareOptions = DEFAULT_COMPARE_OPTIONS,
): TableCompareSummary {
  const results: RowCompareResult[] = [];
  const usedForm = new Set<number>();
  const excludedTissues = new Set<string>();

  for (const wb of workbookRows) {
    if (!wb.tissue.trim() && !wb.pathology.trim()) continue;
    if (isNotIncluded(wb.pos, wb.n)) {
      excludedTissues.add(normalizeText(wb.tissue, options).toLowerCase());
      continue;
    }

    const expectedPath = expectedFormPathology(wb, options);
    const matchIndex = formRows.findIndex((fr, idx) => {
      if (usedForm.has(idx)) return false;
      return tissuesMatch(wb.tissue, fr.tissue, options);
    });

    if (matchIndex === -1) {
      results.push({
        key: workbookRowKey(wb),
        kind,
        status: "missing-in-form",
        workbook: wb,
        expectedFormPathology: expectedPath,
        diffs: [
          {
            field: "tissue",
            workbook: wb.tissue,
            form: "",
          },
        ],
      });
      continue;
    }

    usedForm.add(matchIndex);
    const form = formRows[matchIndex];
    const diffs: CellDiff[] = [];

    if (!eq(wb.tissue, form.tissue, options)) {
      diffs.push({ field: "tissue", workbook: wb.tissue, form: form.tissue });
    }

    // Pathology: when a legend exists, form Pathology must include it (NCL-FRM-000146).
    const pathOk = (() => {
      if (wb.legendCharacter && options.mergeLegendIntoPathology) {
        return pathologyIncludesLegend(
          form.pathology,
          wb.pathology,
          wb.legendCharacter,
          options,
        );
      }
      return (
        eq(expectedPath, form.pathology, options) ||
        eq(wb.pathology, form.pathology, options)
      );
    })();

    if (!pathOk) {
      diffs.push({
        field: "pathology",
        workbook: expectedPath || wb.pathology,
        form: form.pathology,
      });
      if (wb.legendCharacter && options.mergeLegendIntoPathology) {
        const hasLegend = normalizeText(form.pathology, options).includes(
          normalizeText(wb.legendCharacter, options),
        );
        if (!hasLegend) {
          diffs.push({
            field: "legend",
            workbook: wb.legendCharacter,
            form: "(not found in form Pathology)",
          });
        }
      }
    }

    const wbCounts = splitPosN(wb.pos, wb.n);
    const formCounts = splitPosN(form.pos, form.n);
    if (!eq(wbCounts.pos, formCounts.pos, options)) {
      diffs.push({ field: "pos", workbook: wbCounts.pos, form: formCounts.pos });
    }
    if (!eq(wbCounts.n, formCounts.n, options)) {
      diffs.push({ field: "n", workbook: wbCounts.n, form: formCounts.n });
    }
    // Comments only on Normal Table 3. Blank workbook + filled Word is OK.
    if (kind === "normal") {
      const wbComment = normalizeText(wb.comments, options);
      const formComment = normalizeText(form.comments, options);
      if (wbComment && wbComment !== formComment) {
        diffs.push({ field: "comments", workbook: wb.comments, form: form.comments });
      }
    }

    results.push({
      key: workbookRowKey(wb),
      kind,
      status: diffs.length === 0 ? "match" : "mismatch",
      workbook: wb,
      form,
      expectedFormPathology: expectedPath,
      diffs,
    });
  }

  formRows.forEach((fr, idx) => {
    if (usedForm.has(idx)) return;
    if (!fr.tissue.trim() && !fr.pathology.trim()) return;
    if (isNotIncluded(fr.pos, fr.n)) return;
    if (excludedTissues.has(normalizeText(fr.tissue, options).toLowerCase())) return;
    results.push({
      key: formRowKey(fr),
      kind,
      status: "missing-in-workbook",
      form: fr,
      diffs: [{ field: "tissue", workbook: "", form: fr.tissue }],
    });
  });

  const matched = results.filter((r) => r.status === "match").length;
  const mismatched = results.filter((r) => r.status === "mismatch").length;
  const missingInForm = results.filter((r) => r.status === "missing-in-form").length;
  const missingInWorkbook = results.filter(
    (r) => r.status === "missing-in-workbook",
  ).length;

  return {
    kind,
    results,
    matched,
    mismatched,
    missingInForm,
    missingInWorkbook,
    passed: mismatched === 0 && missingInForm === 0 && missingInWorkbook === 0 && matched > 0,
  };
}

function tissuesMatch(a: string, b: string, options: CompareOptions): boolean {
  return eq(a, b, options);
}

function eq(a: string, b: string, options: CompareOptions): boolean {
  return normalizeText(a, options) === normalizeText(b, options);
}

function pathologyIncludesLegend(
  formPathology: string,
  workbookPathology: string,
  legend: string,
  options: CompareOptions,
): boolean {
  const fp = normalizeText(formPathology, options);
  const wp = normalizeText(workbookPathology, options);
  const lg = normalizeText(legend, options);
  if (!lg) return eq(workbookPathology, formPathology, options);
  // Form pathology equals workbook pathology + legend (with optional space)
  const candidates = [
    normalizeText(`${workbookPathology}${legend}`, options),
    normalizeText(`${workbookPathology} ${legend}`, options),
    normalizeText(`${legend}${workbookPathology}`, options),
  ];
  if (candidates.includes(fp)) return true;
  return fp.includes(wp) && fp.includes(lg);
}

/** Demo workbook rows (subset) representing a filled Final Table - Normal. */
export const DEMO_WORKBOOK_NORMAL: WorkbookRow[] = [
  {
    tissue: "Cerebrum (grey matter tissue)",
    pathology: "Normal",
    legendCharacter: "",
    pos: "0",
    n: "3",
    comments: "",
  },
  {
    tissue: "Tonsil",
    pathology: "Normal",
    legendCharacter: "",
    pos: "3",
    n: "3",
    comments: "Lymphocytes positive",
  },
  {
    tissue: "Liver",
    pathology: "Normal",
    legendCharacter: "",
    pos: "0",
    n: "3",
    comments: "",
  },
  {
    tissue: "Colon",
    pathology: "Normal",
    legendCharacter: "",
    pos: "2",
    n: "3",
    comments: "Focal epithelial staining",
  },
];

export const DEMO_WORKBOOK_ABNORMAL: WorkbookRow[] = [
  {
    tissue: "Colon",
    pathology: "Adenocarcinoma",
    legendCharacter: "*",
    pos: "5",
    n: "5",
    comments: "Membranous staining",
  },
  {
    tissue: "Breast",
    pathology: "Invasive ductal carcinoma",
    legendCharacter: "†",
    pos: "4",
    n: "5",
    comments: "",
  },
];

/** Perfect paste into PCS Form Table 3 / 4 (legend merged into pathology). */
export const DEMO_FORM_NORMAL_MATCH: FormRow[] = DEMO_WORKBOOK_NORMAL.map((r) => ({
  tissue: r.tissue,
  pathology: r.pathology,
  pos: r.pos,
  n: r.n,
  comments: r.comments,
}));

export const DEMO_FORM_ABNORMAL_MATCH: FormRow[] = DEMO_WORKBOOK_ABNORMAL.map((r) => ({
  tissue: r.tissue,
  pathology: `${r.pathology}${r.legendCharacter}`,
  pos: r.pos,
  n: r.n,
  comments: r.comments,
}));

/** Intentional transcription errors for demo. */
export const DEMO_FORM_NORMAL_ERRORS: FormRow[] = [
  {
    tissue: "Cerebrum (grey matter tissue)",
    pathology: "Normal",
    pos: "0",
    n: "3",
    comments: "",
  },
  {
    tissue: "Tonsil",
    pathology: "Normal",
    pos: "2", // wrong #pos
    n: "3",
    comments: "Lymphocytes positive",
  },
  {
    tissue: "Liver",
    pathology: "Normal",
    pos: "0",
    n: "3",
    comments: "",
  },
  // Colon missing from form
];

export const DEMO_FORM_ABNORMAL_ERRORS: FormRow[] = [
  {
    tissue: "Colon",
    pathology: "Adenocarcinoma", // missing legend *
    pos: "5",
    n: "5",
    comments: "Membranous staining",
  },
  {
    tissue: "Breast",
    pathology: "Invasive ductal carcinoma†",
    pos: "4",
    n: "5",
    comments: "",
  },
  {
    tissue: "Lung", // extra row not in workbook
    pathology: "Squamous cell carcinoma",
    pos: "1",
    n: "1",
    comments: "",
  },
];

export function formRowsToPaste(rows: FormRow[]): string {
  const header = "Tissue\tPathology\t#pos\tn\tComments";
  const body = rows.map(
    (r) => `${r.tissue}\t${r.pathology}\t${r.pos}\t${r.n}\t${r.comments}`,
  );
  return [header, ...body].join("\n");
}
