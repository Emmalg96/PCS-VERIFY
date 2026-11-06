"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Diff,
  Download,
  Eraser,
  FileSpreadsheet,
  FileText,
  Loader2,
  Sparkles,
  Upload,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import type { ParsedFormTables } from "@/lib/parse-form";
import { buildVerificationReport } from "@/lib/report";
import {
  DEMO_FORM_ABNORMAL_ERRORS,
  DEMO_FORM_ABNORMAL_MATCH,
  DEMO_FORM_NORMAL_ERRORS,
  DEMO_FORM_NORMAL_MATCH,
  DEMO_WORKBOOK_ABNORMAL,
  DEMO_WORKBOOK_NORMAL,
  DEFAULT_COMPARE_OPTIONS,
  compareTables,
  formRowsToPaste,
  parseFormTablePaste,
  type CompareOptions,
  type FormRow,
  type ParsedWorkbookTables,
  type RowCompareResult,
  type TableCompareSummary,
  type WorkbookRow,
} from "@/lib/pcs-tables";
import { cn } from "@/lib/utils";

function StatusBadge({ status }: { status: RowCompareResult["status"] }) {
  if (status === "match") {
    return (
      <Badge className="bg-[var(--pcs-pass)] text-white hover:bg-[var(--pcs-pass)]">
        Match
      </Badge>
    );
  }
  const label =
    status === "mismatch"
      ? "Mismatch"
      : status === "missing-in-form"
        ? "Missing in Word"
        : "Extra in Word";
  return <Badge variant="destructive">{label}</Badge>;
}

function WorkbookCell({
  row,
  expectedPath,
}: {
  row: WorkbookRow;
  expectedPath?: string;
}) {
  return (
    <div className="space-y-0.5">
      <div>Path: {row.pathology || "—"}</div>
      {row.legendCharacter ? <div>Legend: {row.legendCharacter}</div> : null}
      {expectedPath && expectedPath !== row.pathology ? (
        <div className="text-muted-foreground">Word expects: {expectedPath}</div>
      ) : null}
      <div>
        {row.pos || "—"} / {row.n || "—"}
      </div>
      {row.comments ? <div>Notes: {row.comments}</div> : null}
    </div>
  );
}

function FormCell({ row }: { row: FormRow }) {
  return (
    <div className="space-y-0.5">
      <div>Path: {row.pathology || "—"}</div>
      <div>
        {row.pos || "—"} / {row.n || "—"}
      </div>
      {row.comments ? <div>Notes: {row.comments}</div> : null}
    </div>
  );
}

function ResultsTable({ summary }: { summary: TableCompareSummary }) {
  if (summary.results.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No rows to compare for this table.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2.5 font-medium">Tissue</th>
            <th className="px-3 py-2.5 font-medium">Excel (Workbook)</th>
            <th className="px-3 py-2.5 font-medium">Word (PCS Form)</th>
            <th className="px-3 py-2.5 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {summary.results.map((row) => (
            <tr
              key={`${row.kind}-${row.key}-${row.status}`}
              className={cn(
                "border-t border-border/80 align-top",
                row.status === "match" && "bg-[var(--pcs-pass-soft)]/40",
                row.status !== "match" && "bg-destructive/5",
              )}
            >
              <td className="px-3 py-2.5 font-medium">
                {row.workbook?.tissue || row.form?.tissue || "—"}
              </td>
              <td className="px-3 py-2.5 font-mono text-xs">
                {row.workbook ? (
                  <WorkbookCell row={row.workbook} expectedPath={row.expectedFormPathology} />
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
              <td className="px-3 py-2.5 font-mono text-xs">
                {row.form ? (
                  <FormCell row={row.form} />
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
              <td className="px-3 py-2.5">
                <div className="flex flex-col gap-1">
                  <StatusBadge status={row.status} />
                  {row.diffs.map((d, i) => (
                    <span key={i} className="text-xs text-destructive">
                      {d.field}: “{d.workbook || "—"}” ≠ “{d.form || "—"}”
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UploadCard({
  title,
  subtitle,
  accept,
  uploading,
  onFile,
  icon,
  children,
}: {
  title: string;
  subtitle: string;
  accept: string;
  uploading: boolean;
  onFile: (file: File | null) => void;
  icon: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <section className="pcs-panel space-y-4">
      <div>
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--pcs-accent)]">
          {subtitle}
        </p>
        <h2 className="mt-1 font-[family-name:var(--font-display)] text-xl sm:text-2xl">
          {title}
        </h2>
      </div>
      <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--pcs-accent)]/40 bg-[var(--pcs-accent-soft)]/40 px-4 py-8 text-center transition-colors hover:bg-[var(--pcs-accent-soft)]/70">
        {icon}
        <span className="text-sm font-medium">
          {uploading ? "Parsing…" : `Drop or choose file`}
        </span>
        <input
          type="file"
          accept={accept}
          className="sr-only"
          disabled={uploading}
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        />
      </label>
      {uploading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Reading document…
        </p>
      )}
      {children}
    </section>
  );
}

export function PcsVerificationApp() {
  const [workbook, setWorkbook] = useState<ParsedWorkbookTables | null>(null);
  const [formMeta, setFormMeta] = useState<ParsedFormTables | null>(null);
  const [normalPaste, setNormalPaste] = useState("");
  const [abnormalPaste, setAbnormalPaste] = useState("");
  const [options, setOptions] = useState<CompareOptions>(DEFAULT_COMPARE_OPTIONS);
  const [compared, setCompared] = useState(false);
  const [converting, setConverting] = useState(false);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [uploadingWb, setUploadingWb] = useState(false);
  const [uploadingForm, setUploadingForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const formNormal = useMemo(() => parseFormTablePaste(normalPaste), [normalPaste]);
  const formAbnormal = useMemo(
    () => parseFormTablePaste(abnormalPaste),
    [abnormalPaste],
  );

  const normalSummary = useMemo(() => {
    if (!workbook) return null;
    return compareTables("normal", workbook.normal, formNormal, options);
  }, [workbook, formNormal, options]);

  const abnormalSummary = useMemo(() => {
    if (!workbook) return null;
    return compareTables("abnormal", workbook.abnormal, formAbnormal, options);
  }, [workbook, formAbnormal, options]);

  const abnormalVacuous =
    !!abnormalSummary &&
    abnormalSummary.matched === 0 &&
    abnormalSummary.mismatched === 0 &&
    abnormalSummary.missingInForm === 0 &&
    abnormalSummary.missingInWorkbook === 0;

  const overallPassed =
    compared &&
    !!normalSummary &&
    !!abnormalSummary &&
    normalSummary.passed &&
    (abnormalSummary.passed || abnormalVacuous);

  const issueCount = normalSummary && abnormalSummary
    ? normalSummary.mismatched +
      normalSummary.missingInForm +
      normalSummary.missingInWorkbook +
      abnormalSummary.mismatched +
      abnormalSummary.missingInForm +
      abnormalSummary.missingInWorkbook
    : 0;

  async function uploadWorkbook(file: File | null) {
    if (!file) return;
    setPdfFile(file);
    setUploadingWb(true);
    setError(null);
    setCompared(false);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/parse-workbook", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Workbook upload failed");
      setWorkbook(data as ParsedWorkbookTables);
      const kind = file.name.toLowerCase().endsWith(".pdf") ? "PDF" : "Excel";
      setNote(
        `${kind} loaded: ${data.normal.length} normal + ${data.abnormal.length} abnormal Final Table row(s).`,
      );
    } catch (err) {
      setWorkbook(null);
      setError(err instanceof Error ? err.message : "Workbook upload failed");
    } finally {
      setUploadingWb(false);
    }
  }

  async function convertPdfToWord() {
    const file = pdfFile;
    if (!file) {
      setError("Upload an approved workbook PDF (or Excel) first.");
      return;
    }
    setConverting(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/pdf-to-word", { method: "POST", body });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "PDF→Word conversion failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        file.name.replace(/\.(pdf|xlsx|xlsm)$/i, "") + "_PCS_TABLES_4.1_4.2.docx";
      a.click();
      URL.revokeObjectURL(url);
      const n = res.headers.get("X-PCS-Normal-Count");
      const ab = res.headers.get("X-PCS-Abnormal-Count");
      setNote(
        `Downloaded Word §4.1 / §4.2 tables (${n ?? "?"} normal, ${ab ?? "?"} abnormal). Legend symbols are superscripted in Pathology.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF→Word conversion failed");
    } finally {
      setConverting(false);
    }
  }

  async function uploadForm(file: File | null) {
    if (!file) return;
    setUploadingForm(true);
    setError(null);
    setCompared(false);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/parse-form", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Word upload failed");
      const parsed = data as ParsedFormTables;
      setFormMeta(parsed);
      setNormalPaste(formRowsToPaste(parsed.normal));
      setAbnormalPaste(formRowsToPaste(parsed.abnormal));
      setNote(
        `Word loaded: ${parsed.normal.length} Table 3 row(s), ${parsed.abnormal.length} Table 4 row(s) from ${file.name}.`,
      );
    } catch (err) {
      setFormMeta(null);
      setError(err instanceof Error ? err.message : "Word upload failed");
    } finally {
      setUploadingForm(false);
    }
  }

  function loadErrorDemo() {
    setWorkbook({
      normal: DEMO_WORKBOOK_NORMAL,
      abnormal: DEMO_WORKBOOK_ABNORMAL,
      fileName: "demo-workbook.xlsx",
      productName: "Demo Antibody (Clone A)",
    });
    setFormMeta({
      normal: DEMO_FORM_NORMAL_ERRORS,
      abnormal: DEMO_FORM_ABNORMAL_ERRORS,
      fileName: "PCS_FORM_TABLES_ERRORS.docx",
    });
    setNormalPaste(formRowsToPaste(DEMO_FORM_NORMAL_ERRORS));
    setAbnormalPaste(formRowsToPaste(DEMO_FORM_ABNORMAL_ERRORS));
    setCompared(true);
    setError(null);
    setNote(
      "Demo with errors: wrong Tonsil #pos, missing Colon (normal), missing legend * on Adenocarcinoma, extra Lung row in Word.",
    );
  }

  function loadMatchDemo() {
    setWorkbook({
      normal: DEMO_WORKBOOK_NORMAL,
      abnormal: DEMO_WORKBOOK_ABNORMAL,
      fileName: "demo-workbook.xlsx",
      productName: "Demo Antibody (Clone A)",
    });
    setFormMeta({
      normal: DEMO_FORM_NORMAL_MATCH,
      abnormal: DEMO_FORM_ABNORMAL_MATCH,
      fileName: "PCS_FORM_TABLES_MATCH.docx",
    });
    setNormalPaste(formRowsToPaste(DEMO_FORM_NORMAL_MATCH));
    setAbnormalPaste(formRowsToPaste(DEMO_FORM_ABNORMAL_MATCH));
    setCompared(true);
    setError(null);
    setNote("Demo clean match: Word Tables 3/4 match Excel Final Tables (legend in Pathology).");
  }

  function clearAll() {
    setWorkbook(null);
    setFormMeta(null);
    setNormalPaste("");
    setAbnormalPaste("");
    setCompared(false);
    setError(null);
    setNote(null);
  }

  function downloadReport() {
    if (!workbook || !normalSummary || !abnormalSummary) return;
    const text = buildVerificationReport({
      workbook,
      formFileName: formMeta?.fileName,
      normal: normalSummary,
      abnormal: abnormalSummary,
      overallPassed: !!overallPassed,
      generatedAt: new Date().toISOString(),
    });
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pcs-verification-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-8">
      <section className="pcs-panel space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <p className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Excel → Word verification
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Upload the <strong className="font-medium text-foreground">PCS Workbook</strong>{" "}
              (.xlsx) and the filled{" "}
              <strong className="font-medium text-foreground">Product Claims Summary</strong>{" "}
              (.docx). The tool compares Final Tables to Word Tables 3 and 4 — spelling,
              `#pos`/`n`, comments, and abnormal legend characters in Pathology.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" onClick={loadErrorDemo}>
              <Sparkles />
              Demo with errors
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={loadMatchDemo}>
              <CheckCircle2 />
              Demo clean match
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={clearAll}>
              <Eraser />
              Clear
            </Button>
          </div>
        </div>

        <Separator />

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <p className="text-sm font-medium">Compare options</p>
          {(
            [
              ["ignoreWhitespace", "Ignore extra spaces"],
              ["ignoreCase", "Ignore letter case"],
              ["mergeLegendIntoPathology", "Expect legend in Word Pathology"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={options[key]}
                onCheckedChange={(v) => {
                  setOptions((prev) => ({ ...prev, [key]: v === true }));
                  setCompared(false);
                }}
              />
              {label}
            </label>
          ))}
        </div>

        {note && (
          <Alert>
            <FileSpreadsheet />
            <AlertTitle>Ready</AlertTitle>
            <AlertDescription>{note}</AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Could not load document</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <UploadCard
          subtitle="Source of truth · NCL-FRM-001659 PDF (or Excel)"
          title="Approved PCS Workbook"
          accept=".pdf,.xlsx,.xlsm,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          uploading={uploadingWb}
          onFile={uploadWorkbook}
          icon={<Upload className="size-6 text-[var(--pcs-accent)]" />}
        >
          <p className="text-xs text-muted-foreground">
            Prefer the approved PDF extract (§3.7.8: Sign Off + Final Tables). Also
            accepts Excel. Sample:{" "}
            <a className="underline" href="/samples/PCS_WORKBOOK_FINAL_TABLES.pdf">
              /samples/PCS_WORKBOOK_FINAL_TABLES.pdf
            </a>
          </p>
          {workbook && (
            <div className="space-y-2 text-sm">
              <p>
                <span className="font-medium">File:</span> {workbook.fileName}
              </p>
              <p>
                Normal: <span className="font-mono">{workbook.normal.length}</span>
                {" · "}
                Abnormal: <span className="font-mono">{workbook.abnormal.length}</span>
              </p>
              <Button
                type="button"
                onClick={convertPdfToWord}
                disabled={converting || !pdfFile}
                className="gap-2"
              >
                {converting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Download className="size-4" />
                )}
                Convert to Word (§4.1 / §4.2)
              </Button>
            </div>
          )}
        </UploadCard>

        <UploadCard
          subtitle="Destination · NCL-FRM-000146"
          title="Product Claims Summary (Word)"
          accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          uploading={uploadingForm}
          onFile={uploadForm}
          icon={<FileText className="size-6 text-[var(--pcs-accent)]" />}
        >
          <p className="text-xs text-muted-foreground">
            Extracts §4.1 / §4.2 tissue tables (Table 3 / 4 captions also OK). Samples:{" "}
            <a className="underline" href="/samples/PCS_FORM_TABLES_MATCH.docx">
              match
            </a>
            {" · "}
            <a className="underline" href="/samples/PCS_FORM_TABLES_ERRORS.docx">
              errors
            </a>
          </p>
          {formMeta && (
            <p className="text-sm">
              <span className="font-medium">File:</span> {formMeta.fileName}
              {" · "}
              T3 <span className="font-mono">{formMeta.normal.length}</span>
              {" · "}
              T4 <span className="font-mono">{formMeta.abnormal.length}</span>
            </p>
          )}
        </UploadCard>
      </div>

      <section className="pcs-panel space-y-4">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg">
            Extracted Word tables (editable)
          </h3>
          <p className="text-sm text-muted-foreground">
            Auto-filled from the Word upload. You can also paste TSV from Word if needed.
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="normal-paste">§4.1 / Table 3 — Normal</Label>
            <Textarea
              id="normal-paste"
              className="min-h-40 font-mono text-xs"
              value={normalPaste}
              onChange={(e) => {
                setNormalPaste(e.target.value);
                setCompared(false);
              }}
            />
            <p className="text-xs text-muted-foreground">{formNormal.length} row(s)</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="abnormal-paste">§4.2 / Table 4 — Abnormal</Label>
            <Textarea
              id="abnormal-paste"
              className="min-h-40 font-mono text-xs"
              value={abnormalPaste}
              onChange={(e) => {
                setAbnormalPaste(e.target.value);
                setCompared(false);
              }}
            />
            <p className="text-xs text-muted-foreground">
              {formAbnormal.length} row(s) — legend should be inside Pathology
            </p>
          </div>
        </div>
      </section>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Button
          type="button"
          size="lg"
          className="pcs-cta"
          disabled={!workbook || (formNormal.length === 0 && formAbnormal.length === 0)}
          onClick={() => setCompared(true)}
        >
          <Diff />
          Verify Excel → Word
        </Button>
        {compared && normalSummary && abnormalSummary && (
          <Button type="button" variant="outline" size="lg" onClick={downloadReport}>
            <Download />
            Download report
          </Button>
        )}
      </div>

      {compared && normalSummary && abnormalSummary && (
        <section className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="pcs-panel space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Result
                </p>
                <h2 className="mt-1 font-[family-name:var(--font-display)] text-2xl">
                  Verification
                </h2>
              </div>
              {overallPassed ? (
                <Badge className="bg-[var(--pcs-pass)] text-white hover:bg-[var(--pcs-pass)]">
                  Passed
                </Badge>
              ) : (
                <Badge variant="destructive">
                  {issueCount} issue{issueCount === 1 ? "" : "s"}
                </Badge>
              )}
            </div>

            {overallPassed ? (
              <Alert className="border-[var(--pcs-pass)]/30 bg-[var(--pcs-pass-soft)] text-foreground">
                <CheckCircle2 className="text-[var(--pcs-pass)]" />
                <AlertTitle>Excel and Word tables match</AlertTitle>
                <AlertDescription>
                  Tables 3 and 4 align with the workbook Final Tables (including abnormal
                  legend characters).
                </AlertDescription>
              </Alert>
            ) : (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertTitle>Differences found</AlertTitle>
                <AlertDescription>
                  Normal: {normalSummary.mismatched} mismatch
                  {normalSummary.mismatched === 1 ? "" : "es"},{" "}
                  {normalSummary.missingInForm} missing in Word,{" "}
                  {normalSummary.missingInWorkbook} extra in Word. Abnormal:{" "}
                  {abnormalSummary.mismatched} mismatch
                  {abnormalSummary.mismatched === 1 ? "" : "es"},{" "}
                  {abnormalSummary.missingInForm} missing in Word,{" "}
                  {abnormalSummary.missingInWorkbook} extra in Word.
                </AlertDescription>
              </Alert>
            )}
          </div>

          <div className="pcs-panel space-y-3">
            <h3 className="font-[family-name:var(--font-display)] text-lg">
              §4.1 / Table 3 — Normal
            </h3>
            <ResultsTable summary={normalSummary} />
          </div>

          <div className="pcs-panel space-y-3">
            <h3 className="font-[family-name:var(--font-display)] text-lg">
              §4.2 / Table 4 — Abnormal
            </h3>
            <ResultsTable summary={abnormalSummary} />
          </div>
        </section>
      )}
    </div>
  );
}
