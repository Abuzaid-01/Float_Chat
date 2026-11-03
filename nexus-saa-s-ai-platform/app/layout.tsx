import React from "react";
import type { Metadata } from "next";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";
import { GeistPixelLine } from "geist/font/pixel";
import "./globals.css";
import "./observatory.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument",
});

export const metadata: Metadata = {
  title: "FloatChat AI — Conversational Oceanography & ARGO Float RAG Platform",
  description:
    "Explore 1.2M+ ARGO ocean float measurements across the Arabian Sea, Bay of Bengal, and Indian Ocean with AI natural language queries, hybrid search, and zero SQL hallucinations.",
  keywords: [
    "ARGO Float",
    "Oceanography",
    "RAG AI",
    "Ocean Data",
    "PostgreSQL",
    "Marine Science",
    "FAISS",
    "BM25",
  ],
  authors: [{ name: "Abuzaid", url: "https://github.com/Abuzaid-01" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} ${instrumentSerif.variable} ${GeistPixelLine.variable} font-sans antialiased bg-background text-foreground`}
      >
        {children}
      </body>
    </html>
  );
}
