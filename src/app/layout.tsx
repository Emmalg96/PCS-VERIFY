import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, Sora } from "next/font/google";
import "./globals.css";

const display = Sora({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const sans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "PCS Verification · Excel → Word",
  description:
    "Verify PCS Workbook Final Tables (NCL-FRM-001659) against Product Claims Summary (NCL-FRM-000146) §4.1 / §4.2 per NCL-WI-000277 Rev 6.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
