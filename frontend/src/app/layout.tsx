import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VedaAI - AI Teacher's Toolkit",
  description: "Assessment Extraction & Answer Mapping",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F5F5F5]">{children}</body>
    </html>
  );
}
