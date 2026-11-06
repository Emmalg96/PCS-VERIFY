import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import path from "node:path";
import {
  DEMO_FORM_ABNORMAL_ERRORS,
  DEMO_FORM_ABNORMAL_MATCH,
  DEMO_FORM_NORMAL_ERRORS,
  DEMO_FORM_NORMAL_MATCH,
  DEMO_WORKBOOK_ABNORMAL,
  DEMO_WORKBOOK_NORMAL,
  compareTables,
  expectedFormPathology,
  formRowsToPaste,
  parseFormTablePaste,
} from "./pcs-tables";
import { parsePcsWorkbookBuffer } from "./parse-workbook";

describe("parseFormTablePaste", () => {
  it("parses TSV with header", () => {
    const text = formRowsToPaste(DEMO_FORM_NORMAL_MATCH);
    const rows = parseFormTablePaste(text);
    assert.equal(rows.length, DEMO_FORM_NORMAL_MATCH.length);
    assert.equal(rows[1].tissue, "Tonsil");
    assert.equal(rows[1].pos, "3");
  });

  it("keeps empty trailing comments column", () => {
    const text = "Tissue\tPathology\t#pos\tn\tComments\nLiver\tNormal\t0\t3\t";
    const rows = parseFormTablePaste(text);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].pos, "0");
    assert.equal(rows[0].n, "3");
    assert.equal(rows[0].comments, "");
  });

  it("parses combined #pos/n column", () => {
    const text = `Tissue\tPathology\t#pos/n\tComments
Tonsil\tNormal\t3 / 3\tLymphocytes positive`;
    const rows = parseFormTablePaste(text);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].pos, "3");
    assert.equal(rows[0].n, "3");
  });
});

describe("compareTables", () => {
  it("passes when form matches workbook (legend merged)", () => {
    const normal = compareTables("normal", DEMO_WORKBOOK_NORMAL, DEMO_FORM_NORMAL_MATCH);
    const abnormal = compareTables(
      "abnormal",
      DEMO_WORKBOOK_ABNORMAL,
      DEMO_FORM_ABNORMAL_MATCH,
    );
    assert.equal(normal.passed, true);
    assert.equal(abnormal.passed, true);
    assert.equal(
      expectedFormPathology(DEMO_WORKBOOK_ABNORMAL[0], {
        ignoreCase: false,
        ignoreWhitespace: true,
        mergeLegendIntoPathology: true,
      }),
      "Adenocarcinoma*",
    );
  });

  it("flags transcription errors", () => {
    const normal = compareTables("normal", DEMO_WORKBOOK_NORMAL, DEMO_FORM_NORMAL_ERRORS);
    assert.equal(normal.passed, false);
    assert.ok(normal.mismatched >= 1);
    assert.ok(normal.missingInForm >= 1);

    const abnormal = compareTables(
      "abnormal",
      DEMO_WORKBOOK_ABNORMAL,
      DEMO_FORM_ABNORMAL_ERRORS,
    );
    assert.equal(abnormal.passed, false);
    assert.ok(abnormal.mismatched >= 1);
    assert.ok(abnormal.missingInWorkbook >= 1);
    const colon = abnormal.results.find((r) => r.workbook?.tissue === "Colon");
    assert.ok(colon?.diffs.some((d) => d.field === "legend" || d.field === "pathology"));
  });
});

describe("parsePcsWorkbookBuffer", () => {
  it("reads Final Table - Normal from sample workbook", async () => {
    const file = path.join(process.cwd(), "public/samples/PCS_WORKBOOK.xlsx");
    const buf = readFileSync(file);
    const tables = await parsePcsWorkbookBuffer(buf, "PCS_WORKBOOK.xlsx");
    assert.ok(tables.normal.length >= 30);
    assert.equal(tables.normal[0].tissue, "Cerebrum (grey matter tissue)");
    assert.equal(tables.normal[0].pathology, "Normal");
    assert.equal(tables.normal[0].pos, "0");
    assert.equal(tables.normal[0].n, "0");
  });
});

describe("parsePcsFormBuffer", () => {
  it("reads tissue tables from sample match docx", async () => {
    const { parsePcsFormBuffer } = await import("./parse-form");
    const file = path.join(process.cwd(), "public/samples/PCS_FORM_TABLES_MATCH.docx");
    const buf = readFileSync(file);
    const tables = await parsePcsFormBuffer(buf, "PCS_FORM_TABLES_MATCH.docx");
    assert.equal(tables.normal.length, 4);
    assert.equal(tables.abnormal.length, 2);
    assert.equal(tables.abnormal[0].pathology, "Adenocarcinoma*");
  });

  it("rejects empty template form without tissue tables", async () => {
    const { parsePcsFormBuffer } = await import("./parse-form");
    const file = path.join(process.cwd(), "public/samples/NCL-FRM-000146_Rev_7.1.docx");
    const buf = readFileSync(file);
    await assert.rejects(
      () => parsePcsFormBuffer(buf, "NCL-FRM-000146_Rev_7.1.docx"),
      /No tissue tables found/,
    );
  });
});
