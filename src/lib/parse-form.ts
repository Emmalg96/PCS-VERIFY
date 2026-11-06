import { spawn } from "node:child_process";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import type { FormRow } from "./pcs-tables";

export type ParsedFormTables = {
  normal: FormRow[];
  abnormal: FormRow[];
  warnings?: string[];
  tableCount?: number;
  fileName?: string;
};

function runPython(script: string, filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", [script, filePath], { cwd: process.cwd() });
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
      if (code !== 0 && !stdout.trim()) {
        reject(new Error(stderr.trim() || `Form parser exited ${code}`));
        return;
      }
      resolve(stdout);
    });
  });
}

export async function parsePcsFormBuffer(
  buffer: Buffer,
  fileName?: string,
): Promise<ParsedFormTables> {
  const dir = await mkdtemp(path.join(tmpdir(), "pcs-form-"));
  const filePath = path.join(dir, fileName || "form.docx");
  const script = path.join(
    /*turbopackIgnore: true*/ process.cwd(),
    "scripts/parse_pcs_form.py",
  );

  try {
    await writeFile(filePath, buffer);
    const raw = await runPython(script, filePath);
    const data = JSON.parse(raw) as ParsedFormTables & { error?: string };
    if (data.error && !(data.normal?.length || data.abnormal?.length)) {
      throw new Error(data.error);
    }
    return {
      normal: data.normal ?? [],
      abnormal: data.abnormal ?? [],
      warnings: data.warnings,
      tableCount: data.tableCount,
      fileName,
    };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}
