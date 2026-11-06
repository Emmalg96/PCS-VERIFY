import { NextResponse } from "next/server";
import { parsePcsWorkbookBuffer } from "@/lib/parse-workbook";
import { parseWorkbookViaPython } from "@/lib/python-bridge";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get("file");
    if (!file || !(file instanceof File)) {
      return NextResponse.json(
        { error: "Upload a PCS Workbook .pdf or .xlsx file." },
        { status: 400 },
      );
    }
    const lower = file.name.toLowerCase();
    const buffer = Buffer.from(await file.arrayBuffer());

    if (lower.endsWith(".pdf")) {
      const tables = await parseWorkbookViaPython(buffer, file.name);
      return NextResponse.json(tables);
    }

    if (!lower.endsWith(".xlsx") && !lower.endsWith(".xlsm")) {
      return NextResponse.json(
        { error: "File must be a .pdf or .xlsx PCS Workbook." },
        { status: 400 },
      );
    }

    const tables = await parsePcsWorkbookBuffer(buffer, file.name);
    return NextResponse.json(tables);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to parse workbook";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
