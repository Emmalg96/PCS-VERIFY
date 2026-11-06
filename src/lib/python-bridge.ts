import { spawn } from "node:child_process";
import { mkdtemp, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

function runPython(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", args, {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONPATH: process.cwd() },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => {
      stdout += d.toString();
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
  });
}

function safeName(fileName: string, fallback: string): string {
  return fileName.replace(/[^\w.\-]+/g, "_") || fallback;
}

export async function pdfOrExcelToWord(
  buffer: Buffer,
  fileName: string,
): Promise<{ docx: Buffer; normalCount: number; abnormalCount: number }> {
  const dir = await mkdtemp(path.join(tmpdir(), "pcs-pdf2word-"));
  const srcPath = path.join(dir, safeName(fileName, "workbook.pdf"));
  const outPath = path.join(dir, "PCS_TABLES_4.1_4.2.docx");
  try {
    await writeFile(srcPath, buffer);
    const { code, stdout, stderr } = await runPython([
      "-m",
      "pcs_verify",
      "pdf-to-word",
      srcPath,
      "-o",
      outPath,
    ]);
    if (code !== 0) {
      throw new Error(stderr.trim() || stdout.trim() || "PDF→Word conversion failed");
    }
    const docx = await readFile(outPath);
    const normalMatch = stdout.match(/Normal \(§4\.1\): (\d+)/);
    const abnormalMatch = stdout.match(/Abnormal \(§4\.2\): (\d+)/);
    return {
      docx,
      normalCount: normalMatch ? Number(normalMatch[1]) : 0,
      abnormalCount: abnormalMatch ? Number(abnormalMatch[1]) : 0,
    };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

export async function parseWorkbookViaPython(
  buffer: Buffer,
  fileName: string,
): Promise<{
  normal: unknown[];
  abnormal: unknown[];
  productName?: string;
  fileName?: string;
}> {
  const dir = await mkdtemp(path.join(tmpdir(), "pcs-parse-wb-"));
  const srcPath = path.join(dir, safeName(fileName, "workbook.pdf"));
  const scriptPath = path.join(dir, "dump_workbook.py");
  try {
    await writeFile(srcPath, buffer);
    const script = [
      "import json, sys",
      "from pathlib import Path",
      `sys.path.insert(0, ${JSON.stringify(process.cwd())})`,
      "from pcs_verify.pdf_workbook import parse_workbook_pdf",
      "from pcs_verify.workbook import parse_workbook",
      `src = Path(${JSON.stringify(srcPath)})`,
      'wb = parse_workbook_pdf(src) if src.suffix.lower() == ".pdf" else parse_workbook(src)',
      "def rows(data):",
      "    return [{",
      '        "tissue": r.tissue,',
      '        "pathology": r.pathology,',
      '        "legendCharacter": r.legend_character,',
      '        "pos": r.pos,',
      '        "n": r.n,',
      '        "comments": r.comments,',
      "    } for r in data]",
      "print(json.dumps({",
      '    "normal": rows(wb.normal),',
      '    "abnormal": rows(wb.abnormal),',
      '    "productName": wb.product_name,',
      '    "fileName": wb.file_name or src.name,',
      "}))",
      "",
    ].join("\n");
    await writeFile(scriptPath, script, "utf-8");
    const { code, stdout, stderr } = await runPython([scriptPath]);
    if (code !== 0) {
      throw new Error(stderr.trim() || stdout.trim() || "Failed to parse workbook");
    }
    return JSON.parse(stdout);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}
