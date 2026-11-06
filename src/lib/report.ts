import type {
  ParsedWorkbookTables,
  TableCompareSummary,
} from "./pcs-tables";

export function buildVerificationReport(args: {
  workbook: ParsedWorkbookTables;
  formFileName?: string;
  normal: TableCompareSummary;
  abnormal: TableCompareSummary;
  overallPassed: boolean;
  generatedAt: string;
}): string {
  const { workbook, formFileName, normal, abnormal, overallPassed, generatedAt } =
    args;

  const lines: string[] = [
    "PCS VERIFICATION REPORT",
    "Workbook Final Tables → Product Claims Summary Tables 3 & 4",
    "============================================================",
    `Generated: ${generatedAt}`,
    `Result: ${overallPassed ? "PASSED" : "FAILED"}`,
    "",
    `Workbook: ${workbook.fileName || "(unnamed)"}`,
    workbook.productName ? `Product: ${workbook.productName}` : "",
    `Form: ${formFileName || "(paste / unnamed)"}`,
    `Workbook rows — Normal: ${workbook.normal.length}, Abnormal: ${workbook.abnormal.length}`,
    "",
    summaryBlock("§4.1 / Table 3 — Normal", normal),
    "",
    summaryBlock("§4.2 / Table 4 — Abnormal", abnormal),
    "",
    "Row details",
    "-----------",
  ].filter(Boolean);

  for (const summary of [normal, abnormal]) {
    lines.push("");
    lines.push(summary.kind === "normal" ? "[Normal]" : "[Abnormal]");
    for (const row of summary.results) {
      const tissue = row.workbook?.tissue || row.form?.tissue || "(unknown)";
      lines.push(`- ${tissue}: ${row.status.toUpperCase()}`);
      for (const d of row.diffs) {
        lines.push(`    ${d.field}: workbook="${d.workbook}" form="${d.form}"`);
      }
    }
  }

  lines.push("");
  lines.push(
    "Rule basis: NCL-WI-000277 Rev 6 §3.7.6–3.7.7 — Final Tables from approved NCL-FRM-001659 into NCL-FRM-000146 §4.1/§4.2; Abnormal Legend Character (Col D) merged into Pathology; SME confirms superscript symbols.",
  );
  return lines.join("\n");
}

function summaryBlock(title: string, s: TableCompareSummary): string {
  return [
    title,
    `  Matched: ${s.matched}`,
    `  Mismatches: ${s.mismatched}`,
    `  Missing in form: ${s.missingInForm}`,
    `  Extra in form: ${s.missingInWorkbook}`,
    `  Table result: ${s.passed ? "PASSED" : s.matched + s.mismatched + s.missingInForm + s.missingInWorkbook === 0 ? "N/A (empty)" : "FAILED"}`,
  ].join("\n");
}
