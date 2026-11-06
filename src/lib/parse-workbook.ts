import { spawn } from "node:child_process";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import type { ParsedWorkbookTables } from "./pcs-tables";

function runPython(script: string, filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", [script, filePath], {
      cwd: process.cwd(),
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
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr.trim() || stdout.trim() || `Parser exited ${code}`));
        return;
      }
      resolve(stdout);
    });
  });
}

/**
 * Parse PCS Workbook Final Tables via openpyxl (reads cached formula results).
 */
export async function parsePcsWorkbookBuffer(
  buffer: Buffer,
  fileName?: string,
): Promise<ParsedWorkbookTables> {
  const dir = await mkdtemp(path.join(tmpdir(), "pcs-wb-"));
  const filePath = path.join(dir, fileName || "workbook.xlsx");
  const script = path.join(/*turbopackIgnore: true*/ process.cwd(), "scripts/parse_pcs_workbook.py");

  try {
    await writeFile(filePath, buffer);
    const raw = await runPython(script, filePath);
    const data = JSON.parse(raw) as ParsedWorkbookTables & { error?: string };
    if (data.error) {
      throw new Error(data.error);
    }
    return {
      normal: data.normal ?? [],
      abnormal: data.abnormal ?? [],
      productName: data.productName,
      fileName,
    };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}
