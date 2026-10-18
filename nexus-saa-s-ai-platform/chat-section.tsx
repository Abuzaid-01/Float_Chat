"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Send,
  Sparkles,
  Code2,
  Database,
  Table as TableIcon,
  Copy,
  Check,
  Clock,
  Zap,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Reveal } from "./reveal";

function cleanMarkdown(text: string): string {
  if (!text) return "";
  let res = text;
  // Clean byte string artifacts e.g. b'5906395 ' -> 5906395
  res = res.replace(/b'([^']+)'/g, (_, inner) => inner.trim());
  res = res.replace(/b"([^"]+)"/g, (_, inner) => inner.trim());
  // Ensure markdown table rows have newlines between them if they were merged:
  // "| col1 | ... | |---|---| | val1 | ... |" -> "| col1 | ... |\n|---|---|\n| val1 | ... |"
  res = res.replace(/\|\s*\|\s*(?=[-\w:])/g, "|\n|");
  return res;
}

function cleanCellValue(val: any): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    return Number.isInteger(val) ? val.toLocaleString() : val.toFixed(3);
  }
  let s = String(val).trim();
  if ((s.startsWith("b'") && s.endsWith("'")) || (s.startsWith('b"') && s.endsWith('"'))) {
    s = s.slice(2, -1).trim();
  }
  return s;
}

interface ChatMessage {
  role: "user" | "ai";
  text: string;
  meta?: {
    intent?: string;
    result_count?: number;
    execution_time?: number;
    route?: string;
  };
  sql?: string | null;
  data?: Array<Record<string, any>> | null;
}

const QUICK_QUERIES = [
  { label: "🌡️ Arabian Sea Temperature", query: "Show temperature in Arabian Sea" },
  { label: "⚖️ Compare Regions", query: "Compare Arabian Sea and Bay of Bengal" },
  { label: "📊 Active Float Count", query: "How many floats are there?" },
  { label: "🔬 Deep Profiles (>1000m)", query: "Show profiles deeper than 1000 meters" },
  { label: "📍 Float 2902696 Trajectory", query: "Show data for float 2902696" },
  { label: "🧪 Dissolved Oxygen", query: "Find dissolved oxygen data" },
];

export function ChatSection() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedSqlIndex, setCopiedSqlIndex] = useState<number | null>(null);
  const [expandedSql, setExpandedSql] = useState<{ [key: number]: boolean }>({});
  const [expandedData, setExpandedData] = useState<{ [key: number]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(queryText?: string) {
    const text = queryText || input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages
        .filter((m) => m.role === "user" || m.role === "ai")
        .slice(-6)
        .map((m) => ({
          role: m.role === "ai" ? "assistant" : "user",
          content: m.text,
        }));

      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          conversation_history: history,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const result = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: result.response || "No response received from the model.",
          meta: {
            intent: result.intent,
            result_count: result.result_count || 0,
            execution_time: result.execution_time || 0,
            route: result.route,
          },
          sql: result.sql || null,
          data: result.data || null,
        },
      ]);
    } catch (err: any) {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: `⚠️ **Connection Error**: ${err.message}. Make sure the FastAPI backend is running and reachable at \`${apiBase}\`.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleCopySql(sql: string, index: number) {
    navigator.clipboard.writeText(sql);
    setCopiedSqlIndex(index);
    setTimeout(() => setCopiedSqlIndex(null), 2000);
  }

  function toggleSql(index: number) {
    setExpandedSql((prev) => ({ ...prev, [index]: !prev[index] }));
  }

  function toggleData(index: number) {
    setExpandedData((prev) => ({ ...prev, [index]: !prev[index] }));
  }

  return (
    <section id="chat" className="relative py-24 overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-cyan-600/10 via-primary/10 to-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <Reveal>
          <div className="text-center max-w-3xl mx-auto mb-10">
            <p className="text-xs font-mono text-cyan-400 uppercase tracking-widest mb-2 flex items-center justify-center gap-2">
              <Activity className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
              Live Query Workspace
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
              Interact with 1.2M+ Ocean Records
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground">
              Type any question below or click a sample query to trigger the Hybrid RAG engine.
            </p>
          </div>
        </Reveal>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap justify-center gap-2 mb-8 max-w-4xl mx-auto">
          {QUICK_QUERIES.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(item.query)}
              disabled={loading}
              className="px-3.5 py-1.5 rounded-full text-xs font-medium bg-card/60 hover:bg-card border border-border/60 hover:border-primary/50 text-foreground/80 hover:text-foreground transition-all duration-200 backdrop-blur-sm shadow-sm disabled:opacity-50"
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Main Chat Terminal Container */}
        <div className="rounded-2xl border border-border/80 bg-card/90 backdrop-blur-xl shadow-2xl overflow-hidden card-shadow">
          {/* Terminal Window Header */}
          <div className="px-5 py-3.5 border-b border-border/60 bg-secondary/30 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <span className="w-3 h-3 rounded-full bg-rose-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
              </div>
              <span className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-cyan-400" />
                floatchat-rag-session // neon-db:5432
              </span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px] text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Connected (FastAPI RAG)
            </div>
          </div>

          {/* Messages Feed */}
          <div className="p-5 sm:p-7 min-h-[380px] max-h-[580px] overflow-y-auto space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-72 text-center text-muted-foreground">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                  <Sparkles className="w-7 h-7 text-primary animate-pulse" />
                </div>
                <h3 className="text-base font-semibold text-foreground mb-1">
                  Ready for Oceanographic Queries
                </h3>
                <p className="text-xs sm:text-sm max-w-md text-muted-foreground">
                  Ask about temperatures, salinity anomalies, float trajectories, or regional comparisons.
                </p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${
                    msg.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  {/* Message Bubble */}
                  <div
                    className={`max-w-3xl rounded-2xl p-4 sm:p-5 text-sm animate-in slide-in-from-bottom-2 duration-500 ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground font-medium shadow-md"
                        : "bg-secondary/40 border border-border/60 text-foreground/90 leading-relaxed shadow-sm w-full"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <div>{msg.text}</div>
                    ) : (
                      <div className="space-y-3 text-foreground/90 leading-relaxed">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({ children }) => (
                              <div className="my-4 w-full overflow-hidden rounded-xl border border-border/80 bg-background/70 shadow-lg backdrop-blur-md">
                                <div className="overflow-x-auto max-w-full">
                                  <table className="w-full border-collapse text-left font-mono text-xs">
                                    {children}
                                  </table>
                                </div>
                              </div>
                            ),
                            thead: ({ children }) => (
                              <thead className="bg-secondary/90 border-b border-border text-cyan-300 font-semibold uppercase tracking-wider text-[11px] sticky top-0">
                                {children}
                              </thead>
                            ),
                            tbody: ({ children }) => (
                              <tbody className="divide-y divide-border/40 text-foreground/90">
                                {children}
                              </tbody>
                            ),
                            tr: ({ children }) => (
                              <tr className="hover:bg-cyan-500/5 transition-colors odd:bg-transparent even:bg-muted/15">
                                {children}
                              </tr>
                            ),
                            th: ({ children }) => (
                              <th className="px-4 py-3 text-cyan-300 font-semibold whitespace-nowrap border-r border-border/20 last:border-r-0">
                                {children}
                              </th>
                            ),
                            td: ({ children }) => (
                              <td className="px-4 py-2.5 text-foreground/85 whitespace-nowrap border-r border-border/20 last:border-r-0 font-mono text-xs">
                                {children}
                              </td>
                            ),
                            h1: ({ children }) => (
                              <h1 className="text-base sm:text-lg font-bold text-foreground mt-4 mb-2 flex items-center gap-2">
                                {children}
                              </h1>
                            ),
                            h2: ({ children }) => (
                              <h2 className="text-sm sm:text-base font-semibold text-foreground mt-3 mb-1.5 flex items-center gap-2">
                                {children}
                              </h2>
                            ),
                            h3: ({ children }) => (
                              <h3 className="text-xs sm:text-sm font-semibold text-cyan-300 mt-3 mb-1">
                                {children}
                              </h3>
                            ),
                            ul: ({ children }) => (
                              <ul className="list-disc list-inside space-y-1.5 my-2.5 text-foreground/90 pl-1">
                                {children}
                              </ul>
                            ),
                            ol: ({ children }) => (
                              <ol className="list-decimal list-inside space-y-1.5 my-2.5 text-foreground/90 pl-1">
                                {children}
                              </ol>
                            ),
                            li: ({ children }) => (
                              <li className="leading-relaxed text-sm">
                                {children}
                              </li>
                            ),
                            p: ({ children }) => (
                              <p className="leading-relaxed my-2 text-sm text-foreground/90">
                                {children}
                              </p>
                            ),
                            code: ({ inline, className, children, ...props }: any) => {
                              return (
                                <code
                                  className="px-1.5 py-0.5 rounded bg-muted/80 text-cyan-300 font-mono text-xs border border-border/50"
                                  {...props}
                                >
                                  {children}
                                </code>
                              );
                            },
                            strong: ({ children }) => (
                              <strong className="font-semibold text-foreground">
                                {children}
                              </strong>
                            ),
                            blockquote: ({ children }) => (
                              <blockquote className="border-l-2 border-cyan-500/50 pl-3 italic text-muted-foreground my-2.5">
                                {children}
                              </blockquote>
                            ),
                            hr: () => (
                              <hr className="my-3.5 border-border/60" />
                            ),
                          }}
                        >
                          {cleanMarkdown(msg.text)}
                        </ReactMarkdown>
                      </div>
                    )}

                    {/* Metadata Badges (for AI) */}
                    {msg.role === "ai" && msg.meta && (
                      <div className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t border-border/40 font-mono text-[11px] text-muted-foreground">
                        {msg.meta.result_count !== undefined && msg.meta.result_count > 0 && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                            <Layers className="w-3 h-3" />
                            {msg.meta.result_count.toLocaleString()} rows
                          </span>
                        )}
                        {msg.meta.route && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            <Zap className="w-3 h-3" />
                            {msg.meta.route.replace("_", " ")}
                          </span>
                        )}
                        {msg.meta.execution_time !== undefined && msg.meta.execution_time > 0 && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                            <Clock className="w-3 h-3" />
                            {msg.meta.execution_time.toFixed(2)}s
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Collapsible SQL Viewer */}
                  {msg.sql && (
                    <div className="w-full max-w-3xl mt-2">
                      <button
                        onClick={() => toggleSql(idx)}
                        className="flex items-center justify-between w-full px-4 py-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 border border-border/50 text-xs font-mono text-cyan-300 transition-colors"
                      >
                        <span className="flex items-center gap-2">
                          <Code2 className="w-3.5 h-3.5" />
                          Generated SQL Query
                        </span>
                        {expandedSql[idx] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {expandedSql[idx] && (
                        <div className="mt-1.5 p-4 rounded-lg bg-black/70 border border-border/70 font-mono text-xs relative overflow-x-auto">
                          <button
                            onClick={() => handleCopySql(msg.sql!, idx)}
                            className="absolute top-3 right-3 px-2.5 py-1 rounded bg-secondary hover:bg-secondary/80 text-foreground text-[11px] flex items-center gap-1.5 border border-border/60 transition-colors"
                          >
                            {copiedSqlIndex === idx ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                Copied
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                Copy SQL
                              </>
                            )}
                          </button>
                          <pre className="text-cyan-300 pr-20 whitespace-pre-wrap leading-relaxed">
                            {msg.sql}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Collapsible Data Table */}
                  {msg.data && msg.data.length > 0 && (
                    <div className="w-full max-w-3xl mt-2">
                      <button
                        onClick={() => toggleData(idx)}
                        className="flex items-center justify-between w-full px-4 py-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 border border-border/50 text-xs font-mono text-indigo-300 transition-colors"
                      >
                        <span className="flex items-center gap-2">
                          <TableIcon className="w-3.5 h-3.5" />
                          Raw Ocean Records ({msg.data.length.toLocaleString()} rows)
                        </span>
                        {expandedData[idx] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {expandedData[idx] && (
                        <div className="mt-2 rounded-xl border border-border/80 overflow-hidden bg-background/80 shadow-md backdrop-blur-md">
                          <div className="overflow-x-auto max-h-80">
                            <table className="w-full text-left font-mono text-xs border-collapse">
                              <thead className="bg-secondary/95 border-b border-border text-cyan-300 uppercase text-[10px] tracking-wider sticky top-0 z-10 backdrop-blur-sm">
                                <tr>
                                  {Object.keys(msg.data[0]).map((key) => (
                                    <th key={key} className="px-3.5 py-2.5 font-semibold whitespace-nowrap border-r border-border/20 last:border-r-0">
                                      {key.replace(/_/g, " ")}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border/30 text-foreground/90">
                                {msg.data.slice(0, 50).map((row, rIdx) => (
                                  <tr key={rIdx} className="hover:bg-cyan-500/5 transition-colors odd:bg-transparent even:bg-muted/15">
                                    {Object.keys(msg.data![0]).map((key) => (
                                      <td key={key} className="px-3.5 py-2 whitespace-nowrap border-r border-border/20 last:border-r-0 text-foreground/80">
                                        {cleanCellValue(row[key])}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          {msg.data.length > 50 && (
                            <div className="p-2.5 text-center text-[11px] font-mono text-muted-foreground border-t border-border/40 bg-secondary/30">
                              Showing first 50 of {msg.data.length.toLocaleString()} records
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}

            {/* Loading State */}
            {loading && (
              <div className="flex items-center gap-3 text-cyan-300 font-mono text-xs p-4 rounded-xl bg-secondary/30 border border-border/50 animate-pulse">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                Executing RAG Pipeline (BM25 + FAISS → Dynamic Schema → Neon DB)...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-4 sm:p-5 border-t border-border/60 bg-secondary/20">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2 sm:gap-3"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about ARGO ocean data (e.g., 'Show temperature in Arabian Sea')..."
                disabled={loading}
                className="flex-1 bg-background/80 border border-border/80 rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/50 font-normal transition-all"
              />
              <Button
                type="submit"
                disabled={loading || !input.trim()}
                className="bg-primary hover:bg-primary/90 text-primary-foreground h-11 px-5 rounded-xl font-medium shadow-md shadow-primary/20 shrink-0"
              >
                <Send className="w-4 h-4 mr-1.5" />
                <span className="hidden sm:inline">Send Query</span>
              </Button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
