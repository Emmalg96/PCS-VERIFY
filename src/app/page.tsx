import { PcsVerificationApp } from "@/components/pcs-verification-app";

export default function Home() {
  return (
    <main className="relative mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
      <header className="pcs-rise mb-10 max-w-3xl">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.2em] text-[var(--pcs-accent)]">
          PCS Check · PDF → Word (§4.1 / §4.2)
        </p>
        <h1 className="pcs-brand-mark mt-3 font-[family-name:var(--font-display)] text-4xl leading-[1.05] tracking-tight text-foreground sm:text-5xl md:text-6xl">
          PCS Verification
        </h1>
        <p className="pcs-rise pcs-rise-delay-1 mt-4 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Convert approved PCS Workbook Final Tables from PDF into Word §4.1 /
          §4.2 (legend characters as superscript), then verify against
          NCL-FRM-000146 — NCL-WI-000277 Rev 6 §3.7.6–3.7.8.
        </p>
      </header>

      <div className="pcs-rise pcs-rise-delay-2">
        <PcsVerificationApp />
      </div>

      <footer className="mt-14 border-t border-border/70 pt-6 text-sm text-muted-foreground">
        <p>
          Upload real filled documents, or try the demos. Sample files live under{" "}
          <span className="font-medium text-foreground">/samples/</span>.
        </p>
      </footer>
    </main>
  );
}
