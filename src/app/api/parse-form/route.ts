import { NextResponse } from "next/server";
import { parsePcsFormBuffer } from "@/lib/parse-form";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get("file");
    if (!file || !(file instanceof File)) {
      return NextResponse.json(
        { error: "Upload a Product Claims Summary .docx file." },
        { status: 400 },
      );
    }
    if (!file.name.toLowerCase().endsWith(".docx")) {
      return NextResponse.json(
        { error: "File must be a .docx Product Claims Summary." },
        { status: 400 },
      );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const tables = await parsePcsFormBuffer(buffer, file.name);
    return NextResponse.json(tables);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to parse form";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
