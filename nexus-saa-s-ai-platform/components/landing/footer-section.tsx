"use client";

import { Waves, Database, Github, Linkedin, ExternalLink } from "lucide-react";

export function FooterSection() {
  return (
    <footer className="relative border-t border-border/80 bg-background/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-14">
        <div className="flex flex-col md:flex-row items-center justify-between gap-8">
          {/* Brand & Mission */}
          <div className="max-w-md text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Waves className="w-4 h-4 text-primary" />
              </div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-cyan-200 to-primary bg-clip-text text-transparent">
                FloatChat AI
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Open conversational AI platform for exploring international ARGO float oceanographic data with zero SQL hallucinations.
            </p>
          </div>

          {/* Quick links & Creator */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground font-mono">
            <a
              href="#chat"
              className="hover:text-cyan-300 transition-colors"
            >
              // LIVE CHAT
            </a>
            <a
              href="#how-it-works"
              className="hover:text-cyan-300 transition-colors"
            >
              // RAG PIPELINE
            </a>
            <a
              href="#features"
              className="hover:text-cyan-300 transition-colors"
            >
              // CAPABILITIES
            </a>
            <a
              href="https://github.com/Abuzaid-01"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground transition-colors text-foreground/80"
            >
              <Github className="w-3.5 h-3.5" />
              GitHub
            </a>
            <a
              href="https://www.linkedin.com/in/abuzaid01"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground transition-colors text-foreground/80"
            >
              <Linkedin className="w-3.5 h-3.5 text-cyan-400" />
              Abuzaid
            </a>
          </div>
        </div>

        {/* Bottom copyright & Status */}
        <div className="mt-10 pt-6 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground/70">
          <p>© 2026 FloatChat AI. Built by Abuzaid. Data provided by the global ARGO Programme.</p>
          <div className="flex items-center gap-2 font-mono text-[11px] text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            PostgreSQL • Groq Llama 3.3 • FAISS Active
          </div>
        </div>
      </div>
    </footer>
  );
}
