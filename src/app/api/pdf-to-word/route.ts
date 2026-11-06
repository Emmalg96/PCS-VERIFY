import { NextResponse } from "next/server";
import { pdfOrExcelToWord } from "@/lib/python-bridge";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get("file");
    if (!file || !(file instanceof File)) {
      return NextResponse.json(
        { error: "Upload an approved PCS Workbook PDF (or Excel)." },
        { status: 400 },
      );
    }
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".pdf") && !lower.endsWith(".xlsx") && !lower.endsWith(".xlsm")) {
      return NextResponse.json(
        { error: "File must be a .pdf or .xlsx PCS Workbook." },
        { status: 400 },
      );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const { docx, normalCount, abnormalCount } = await pdfOrExcelToWord(buffer, file.name);
    const outName = file.name.replace(/\.(pdf|xlsx|xlsm)$/i, "") + "_PCS_TABLES_4.1_4.2.docx";

    return new NextResponse(new Uint8Array(docx), {
      status: 200,
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="${outName}"`,
        "X-PCS-Normal-Count": String(normalCount),
        "X-PCS-Abnormal-Count": String(abnormalCount),
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "PDF→Word failed";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
