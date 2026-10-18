import React from "react";
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { GeistPixelLine } from "geist/font/pixel";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
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
        className={`${inter.variable} ${jetbrainsMono.variable} ${GeistPixelLine.variable} font-sans antialiased bg-background text-foreground`}
      >
        {children}
      </body>
    </html>
  );
}
