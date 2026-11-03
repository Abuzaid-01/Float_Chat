"use client";

import { FormEvent, forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity, ArrowDownToLine, ArrowRight, BarChart3, Bot, Check, Clipboard, Command, CornerDownLeft, FlaskConical,
  MapPin, Radio, RotateCcw, Scale, Send, Sparkles, Square, Trash2, Waves,
} from "lucide-react";
import { API_BASE_URL, ApiError, ChatResponse, ChatTurn, Suggestion, floatchatApi } from "@/lib/api";
import { Reveal } from "@/components/landing/reveal";
import { ResultLens } from "./result-lens";

export type ApiStatus = "checking" | "online" | "offline";

export type CompletedQuery = { question: string; result: ChatResponse };

export type WorkspaceHandle = { ask: (question: string) => void };

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: ChatResponse;
  /** Set when the request itself failed, so the reply can offer a retry. */
  failedQuestion?: string;
};

type WorkspaceProps = {
  status: ApiStatus;
  suggestions: Suggestion[];
  onStatus: (status: ApiStatus) => void;
  onCompleted: (query: CompletedQuery) => void;
  /** Told when a chat request starts and ends: the API answers nothing else meanwhile. */
  onBusy: (busy: boolean) => void;
};

const CATEGORY_ICONS: Record<string, typeof MapPin> = {
  geographic: MapPin,
  comparison: Scale,
  statistics: BarChart3,
  depth: ArrowDownToLine,
  float: Radio,
  bgc: FlaskConical,
  analysis: Activity,
};

/**
 * The backend replies in one piece (no streaming), so these stages are paced
 * on typical timings to show what the pipeline is doing while it works.
 */
const STAGES = [
  { after: 0, label: "Classifying intent" },
  { after: 0.5, label: "Searching similar profiles" },
  { after: 1, label: "Building SQL" },
  { after: 1.6, label: "Querying the database" },
  { after: 3.2, label: "Composing the answer" },
];

/** Undo two artefacts of LLM output: Python byte-string wrappers and table rows fused onto one line. */
function cleanMarkdown(text: string) {
  return text
    .replace(/b'([^']+)'/g, (_, inner: string) => inner.trim())
    .replace(/b"([^"]+)"/g, (_, inner: string) => inner.trim())
    .replace(/\|[ \t]+\|(?=[ \t]*[-:\w])/g, "|\n|");
}

function describeFailure(error: unknown) {
  if (error instanceof ApiError) {
    if (error.kind === "network") {
      return `I can't reach the FloatChat API at \`${API_BASE_URL}\`. Start the backend (\`./start.sh\` from the FloatChat folder), then try again.`;
    }
    if (error.kind === "timeout") return `The API took too long to reply. ${error.message} Try a narrower question.`;
    return `The API returned an error${error.status ? ` (${error.status})` : ""}: ${error.message}`;
  }
  return "Something went wrong while sending your question.";
}

/** Database drivers append the full statement and a docs link; keep the reason only. */
function briefError(error: string) {
  const reason = error.split(/\[SQL:|\(Background on this error/)[0].trim();
  return reason.length > 280 ? `${reason.slice(0, 280)}…` : reason;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="message-action"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        } catch {
          // Clipboard access can be denied; the text stays selectable.
        }
      }}
    >
      {copied ? <Check size={12} /> : <Clipboard size={12} />} {copied ? "Copied" : "Copy answer"}
    </button>
  );
}

function PipelineProgress({ onCancel }: { onCancel: () => void }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const timer = setInterval(() => setElapsed((performance.now() - start) / 1000), 100);
    return () => clearInterval(timer);
  }, []);

  const active = STAGES.reduce((current, stage, index) => (elapsed >= stage.after ? index : current), 0);

  return (
    <div className="pipeline-progress" role="status" aria-label="Working on your question">
      <div className="pipeline-progress__head">
        <span className="sonar" aria-hidden="true" />
        <b>{STAGES[active].label}…</b>
        <time>{elapsed.toFixed(1)} s</time>
        <button type="button" onClick={onCancel}>
          <Square size={10} /> Stop
        </button>
      </div>
      <ol>
        {STAGES.map((stage, index) => (
          <li key={stage.label} className={index < active ? "is-done" : index === active ? "is-active" : ""}>
            <i />
            {stage.label}
          </li>
        ))}
      </ol>
      <p>Most answers arrive within 15 seconds.</p>
    </div>
  );
}

export const Workspace = forwardRef<WorkspaceHandle, WorkspaceProps>(function Workspace(
  { status, suggestions, onStatus, onCompleted, onBusy },
  ref,
) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const feed = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const request = useRef<AbortController | null>(null);
  // Mirrors `messages` so `sendMessage` can build history without a stale closure.
  const transcript = useRef<Message[]>([]);
  transcript.current = messages;

  useEffect(() => {
    const el = feed.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const el = textarea.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [input]);

  useEffect(() => () => request.current?.abort(), []);

  async function sendMessage(value?: string) {
    const question = (value ?? input).trim();
    if (!question || request.current) return;

    const history: ChatTurn[] = transcript.current
      .filter((message) => !message.failedQuestion)
      .slice(-6)
      .map((message) => ({ role: message.role, content: message.text }));
    const controller = new AbortController();
    request.current = controller;

    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", text: question }]);
    setInput("");
    setLoading(true);
    onBusy(true);

    try {
      const result = await floatchatApi.chat(question, history, controller.signal);
      onStatus("online");
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: result.success
            ? result.response || "The API returned an empty answer."
            : "I couldn't complete that query. The pipeline stopped before it produced an answer — it is often worth one more try.",
          result,
          failedQuestion: result.success ? undefined : question,
        },
      ]);
      // Only data queries leave a full trail (retrieval, SQL, rows) to replay.
      if (result.success && result.sql) onCompleted({ question, result });
    } catch (error) {
      const cancelled = error instanceof ApiError && error.kind === "aborted";
      if (error instanceof ApiError && error.kind === "network") onStatus("offline");
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: cancelled ? "Stopped. The question was not answered." : describeFailure(error),
          failedQuestion: question,
        },
      ]);
    } finally {
      request.current = null;
      setLoading(false);
      onBusy(false);
    }
  }

  useImperativeHandle(ref, () => ({ ask: (question: string) => void sendMessage(question) }));

  function clearSession() {
    request.current?.abort();
    setMessages([]);
  }

  return (
    <section className="workspace-section" id="workspace">
      <Reveal>
        <div className="section-heading">
          <div>
            <span className="eyebrow">
              <Command size={13} /> Live query workspace
            </span>
            <h2>
              From question to
              <br />
              <i>verifiable signal.</i>
            </h2>
          </div>
          <p>
            Ask in plain English. FloatChat finds similar profiles, writes read-only SQL, runs it on the ARGO database, and
            answers from the rows that come back — with the chart, table and query beside every reply.
          </p>
        </div>
      </Reveal>

      <Reveal delay={120}>
        <div className="workspace-shell">
          <aside className="workspace-rail">
            <div className="rail-label">Try a question</div>
            {suggestions.slice(0, 6).map((suggestion) => {
              const Icon = CATEGORY_ICONS[suggestion.category] ?? Sparkles;
              return (
                <button key={suggestion.text} type="button" disabled={loading} onClick={() => sendMessage(suggestion.text)}>
                  <Icon size={14} />
                  <span>
                    {suggestion.text}
                    <small>{suggestion.category}</small>
                  </span>
                  <ArrowRight size={13} />
                </button>
              );
            })}
            <div className="rail-foot">
              <span className={`status-dot ${status}`} />
              {status === "online" ? "API connected" : status === "offline" ? "API unreachable" : "Checking API"}
            </div>
          </aside>

          <div className="chat-workspace">
            <div className="workspace-topbar">
              <div>
                <span className={`status-dot ${status}`} />
                <b>Query session</b>
                <small>{API_BASE_URL.replace(/^https?:\/\//, "")}</small>
              </div>
              {messages.length > 0 && (
                <button type="button" className="icon-text-button" onClick={clearSession}>
                  <Trash2 size={13} /> New session
                </button>
              )}
            </div>

            <div className="conversation" ref={feed} aria-live="polite">
              {messages.length === 0 && !loading ? (
                <div className="conversation-empty">
                  <div className="empty-mark">
                    <Waves size={28} />
                  </div>
                  <h3>What would you like to understand?</h3>
                  <p>
                    Ask about temperature, salinity, depth profiles, a region, or a single float. Pick a question on the
                    left to see how an answer looks.
                  </p>
                  {status === "offline" && (
                    <div className="query-error">
                      The API at {API_BASE_URL} is not responding. Run <code>./start.sh</code> in the FloatChat folder to
                      start it.
                    </div>
                  )}
                </div>
              ) : (
                messages.map((message) => (
                  <article key={message.id} className={`message message--${message.role}`}>
                    <div className="message-avatar">{message.role === "user" ? "You" : <Bot size={15} />}</div>
                    <div className="message-body">
                      <div className="message-label">{message.role === "user" ? "You" : "FloatChat"}</div>
                      {message.role === "assistant" ? (
                        <div className="message-markdown">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              table: ({ children }) => (
                                <div className="markdown-table">
                                  <table>{children}</table>
                                </div>
                              ),
                            }}
                          >
                            {cleanMarkdown(message.text)}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p>{message.text}</p>
                      )}

                      {message.result && !message.result.success && (
                        <div className="query-error">{briefError(message.result.error || message.result.response)}</div>
                      )}
                      {message.result && (message.result.data?.length || message.result.sql) ? (
                        <ResultLens result={message.result} />
                      ) : null}

                      {message.role === "assistant" && (
                        <div className="message-actions">
                          {message.failedQuestion ? (
                            <button
                              type="button"
                              className="message-action"
                              disabled={loading}
                              onClick={() => sendMessage(message.failedQuestion)}
                            >
                              <RotateCcw size={12} /> Try again
                            </button>
                          ) : (
                            <CopyButton text={message.text} />
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                ))
              )}
              {loading && <PipelineProgress onCancel={() => request.current?.abort()} />}
            </div>

            <form
              className="composer"
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                sendMessage();
              }}
            >
              <div>
                <textarea
                  ref={textarea}
                  value={input}
                  rows={1}
                  aria-label="Your question about ARGO ocean data"
                  placeholder="Ask about ARGO ocean data…"
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                      event.preventDefault();
                      sendMessage();
                    }
                  }}
                />
                <span>
                  <CornerDownLeft size={11} /> Enter to send
                </span>
              </div>
              <button type="submit" disabled={!input.trim() || loading} aria-label="Send question">
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>
      </Reveal>
    </section>
  );
});
