"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Sparkles,
  Check,
  Copy,
  Pencil,
  ThumbsUp,
  ThumbsDown,
  Shield,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { AuthAttachment } from "./AuthAttachment";

export interface Attachment {
  filename: string;
  path: string;
  mime: string;
  kind: string;
}

export interface Message {
  id?: number;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  attachments?: Attachment[] | null;
  created_at?: string;
  feedback?: string | null;
  thoughts?: string[];
}

interface TableData {
  headers: string[];
  rows: string[][];
}

const MemoizedCodeBlock = React.memo(function MemoizedCodeBlock({
  language,
  codeString,
  isCopied,
  onCopy,
}: {
  language: string;
  codeString: string;
  isCopied: boolean;
  onCopy: (code: string) => void;
}) {
  return (
    <div className="relative group my-3 not-prose">
      <div className="absolute top-3 right-3 z-10">
        <button
          onClick={() => onCopy(codeString)}
          className="p-2 rounded-lg bg-background/90 hover:bg-background text-foreground transition-all shadow-sm border border-border/50"
          aria-label="Copy code"
        >
          {isCopied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        className="rounded-xl !mt-0 !mb-0 !bg-background/95 dark:!bg-[#1e1e1e] border border-border/50 shadow-sm"
      >
        {codeString}
      </SyntaxHighlighter>
    </div>
  );
});

export function parseThoughtsAndCleanText(content: string): { thoughts: string[]; cleanText: string } {
  if (!content) return { thoughts: [], cleanText: "" };

  const thoughts: string[] = [];
  let cleanText = content;

  // Extract closed <think>...</think> blocks
  const thinkRegex = /<think>([\s\S]*?)<\/think>/gi;
  let match: RegExpExecArray | null;
  while ((match = thinkRegex.exec(content)) !== null) {
    if (match[1]?.trim()) {
      const lines = match[1].trim().split("\n").map((l) => l.trim()).filter(Boolean);
      thoughts.push(...lines);
    }
  }

  // Remove closed <think>...</think> blocks
  cleanText = cleanText.replace(/<think>([\s\S]*?)<\/think>/gi, "");

  // Remove orphaned opening or closing <think> / </think> tags
  cleanText = cleanText.replace(/<\/?think>/gi, "");

  // Handle unclosed <think>... blocks if any remain
  cleanText = cleanText.replace(/<think>[\s\S]*/gi, (unclosed) => {
    const rawInner = unclosed.replace(/^<think>/i, "").trim();
    if (rawInner) {
      thoughts.push(...rawInner.split("\n").map((l) => l.trim()).filter(Boolean));
    }
    return "";
  });

  return {
    thoughts,
    cleanText: cleanText.trim(),
  };
}

export function parseMarkdownTables(text: string): (string | TableData)[] {
  if (!text || !text.includes("|")) return [text];

  // Fix concatenated table rows without newlines
  let normalized = text.replace(/\|\s*\|/g, "|\n|");
  normalized = normalized.replace(/\|\s*(-{3,}|:?-+:?)\s*\|/g, (m) => `\n${m.trim()}\n`);

  const lines = normalized.split("\n");
  const result: (string | TableData)[] = [];
  let currentTextBuffer: string[] = [];
  let inTable = false;
  let tableHeaders: string[] = [];
  let tableRows: string[][] = [];

  const isTableSeparator = (line: string) => /^\|(?:\s*:?-+:?\s*\|)+$/.test(line.replace(/\s+/g, ""));
  const isTableRow = (line: string) => line.startsWith("|") && line.endsWith("|") && line.split("|").length >= 3;

  const parseRow = (line: string) => {
    return line
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim());
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (!inTable) {
      if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1].trim())) {
        if (currentTextBuffer.length > 0) {
          result.push(currentTextBuffer.join("\n"));
          currentTextBuffer = [];
        }
        inTable = true;
        tableHeaders = parseRow(line);
        tableRows = [];
        i++; // Skip separator
      } else {
        currentTextBuffer.push(lines[i]);
      }
    } else {
      if (isTableRow(line)) {
        tableRows.push(parseRow(line));
      } else {
        // Table ended
        if (tableHeaders.length > 0) {
          result.push({ headers: tableHeaders, rows: tableRows });
        }
        inTable = false;
        tableHeaders = [];
        tableRows = [];
        currentTextBuffer.push(lines[i]);
      }
    }
  }

  if (inTable && tableHeaders.length > 0) {
    result.push({ headers: tableHeaders, rows: tableRows });
  } else if (currentTextBuffer.length > 0) {
    result.push(currentTextBuffer.join("\n"));
  }

  return result;
}

interface ChatMessageItemProps {
  msg: Message;
  index: number;
  isLast: boolean;
  assistantStreaming: boolean;
  copiedCode: string | null;
  feedback: Record<number, string>;
  onCopy: (text: string) => void;
  onEditPrompt: (text: string) => void;
  onSendFeedback: (id: number, type: "thumbs_up" | "thumbs_down") => void;
  onSelectSuggestion: (sug: string) => void;
  formatTime: (ts?: string) => string;
}

export function ChatMessageItem({
  msg,
  index,
  isLast,
  assistantStreaming,
  copiedCode,
  feedback,
  onCopy,
  onEditPrompt,
  onSendFeedback,
  onSelectSuggestion,
  formatTime,
}: ChatMessageItemProps) {
  return (
    <div
      className={`flex gap-4 group ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
      style={{ animation: "mpIn 200ms ease-out both" }}
    >
      {/* Avatar */}
      <div className="shrink-0 mt-1">
        {msg.role === "user" ? (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-sm">
            <span className="text-[11px] text-white font-semibold">You</span>
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/20 flex items-center justify-center">
            <Sparkles size={16} className="text-primary" />
          </div>
        )}
      </div>

      {/* Message bubble */}
      <div className={`flex-1 min-w-0 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
        {/* Header */}
        <div className={`flex items-center gap-2 mb-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
          <span className="text-xs font-semibold text-foreground">
            {msg.role === "user" ? "You" : "AladdinAI"}
          </span>
          {msg.model && (
            <span className="text-[10px] text-muted-foreground">· {msg.model}</span>
          )}
          {msg.created_at && (
            <span className="text-[10px] text-muted-foreground">
              · {formatTime(msg.created_at)}
            </span>
          )}
        </div>

        {/* Audio attachments */}
        {msg.attachments && msg.attachments.some(a => a.kind === "audio" || a.mime?.startsWith("audio/")) && (
          <div className={`flex flex-wrap gap-2 mb-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.attachments
              .filter(a => a.kind === "audio" || a.mime?.startsWith("audio/"))
              .map((att) => (
                <AuthAttachment key={att.filename} filename={att.filename} mime={att.mime} kind={att.kind} isUser={msg.role === "user"} />
              ))}
          </div>
        )}

        {/* Content bubble */}
        {(Boolean(msg.content) || Boolean(msg.thoughts?.length) || (msg.attachments && msg.attachments.some(a => a.kind !== "audio" && !a.mime?.startsWith("audio/")))) && (
          <div
            className={`rounded-2xl px-4 py-3 ${msg.role === "user"
              ? "bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-md"
              : "bg-muted/50 border border-border/50"
              }`}
          >
            {msg.attachments && msg.attachments.some(a => a.kind !== "audio" && !a.mime?.startsWith("audio/")) && (
              <div className="flex flex-wrap gap-2 mb-3">
                {msg.attachments
                  .filter(a => a.kind !== "audio" && !a.mime?.startsWith("audio/"))
                  .map((att) => (
                    <AuthAttachment key={att.filename} filename={att.filename} mime={att.mime} kind={att.kind} isUser={msg.role === "user"} />
                  ))}
              </div>
            )}
            {(() => {
              const { thoughts: parsedThoughts, cleanText: extractedClean } = parseThoughtsAndCleanText(msg.content || "");
              const displayThoughts = (msg.thoughts && msg.thoughts.length > 0) ? msg.thoughts : parsedThoughts;
              const cleanText = msg.role === "user" ? (msg.content || "") : extractedClean;

              return (
                <>
                  {msg.role === "assistant" && displayThoughts.length > 0 && (
                    <details className="mb-3.5 rounded-xl border border-border/80 bg-card/90 dark:bg-muted/30 text-xs overflow-hidden group shadow-sm transition-all">
                      <summary className="px-3.5 py-2 cursor-pointer font-mono text-[11px] text-muted-foreground hover:text-foreground flex items-center justify-between select-none bg-muted/50 hover:bg-muted/80 transition-colors">
                        <span className="flex items-center gap-2 font-medium">
                          <Sparkles size={13} className="text-primary" />
                          <span className="font-sans font-semibold text-foreground">Thought Process</span>
                          <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-mono border border-primary/20">
                            {displayThoughts.length} step{displayThoughts.length > 1 ? "s" : ""}
                          </span>
                        </span>
                        <span className="text-[10px] text-muted-foreground group-open:rotate-180 transition-transform">▼</span>
                      </summary>
                      <div className="px-3.5 pb-3 pt-2.5 space-y-1.5 font-mono border-t border-border/50 bg-background/50 text-[11px]">
                        {displayThoughts.map((t, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-muted-foreground leading-relaxed">
                            <span className="text-emerald-500 dark:text-emerald-400 font-bold text-[10px] mt-0.5">✓</span>
                            <span className="break-words text-foreground/90">{t}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                  {(cleanText || msg.role === "assistant") && (
                    <div className={`prose prose-sm max-w-none relative ${msg.role === "user"
                      ? "prose-invert prose-headings:text-white prose-p:text-white/95 prose-strong:text-white prose-code:text-white/90"
                      : "dark:prose-invert"
                      } prose-pre:my-3 prose-pre:bg-background/95 dark:prose-pre:bg-[#1e1e1e] prose-pre:border prose-pre:border-border/50 prose-pre:shadow-sm prose-code:text-sm prose-p:leading-relaxed prose-headings:font-semibold`}>
                      {parseMarkdownTables(cleanText || "").map((part, pIdx) => {
                        if (typeof part === "string") {
                          if (!part.trim()) return null;
                          return (
                            <ReactMarkdown
                              key={pIdx}
                              components={{
                                code({ node, className, children, ...props }) {
                                  const match = /language-(\w+)/.exec(className || "");
                                  const codeString = String(children).replace(/\n$/, "");
                                  const isCopied = copiedCode === codeString;
                                  const isBlock = Boolean(match);

                                  return isBlock ? (
                                    <MemoizedCodeBlock
                                      language={match![1]}
                                      codeString={codeString}
                                      isCopied={isCopied}
                                      onCopy={onCopy}
                                    />
                                  ) : (
                                    <code className={`${msg.role === "user"
                                      ? "bg-white/20 text-white"
                                      : "bg-muted/80 dark:bg-muted/60 text-foreground"
                                      } px-1.5 py-0.5 rounded text-[13px] font-mono`} {...props}>
                                      {children}
                                    </code>
                                  );
                                },
                              }}
                            >
                              {part}
                            </ReactMarkdown>
                          );
                        }

                        return (
                          <div key={pIdx} className="my-4 overflow-x-auto rounded-xl border border-border/80 bg-card/90 dark:bg-muted/20 shadow-md not-prose">
                            <table className="w-full text-left text-xs border-collapse font-sans">
                              <thead className="bg-muted/80 border-b border-border text-foreground font-semibold">
                                <tr>
                                  {part.headers.map((h, hIdx) => (
                                    <th key={hIdx} className="px-3.5 py-2.5 font-semibold text-foreground border-r last:border-r-0 border-border/40">
                                      {h}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border/40 text-muted-foreground">
                                {part.rows.map((row, rIdx) => (
                                  <tr key={rIdx} className="hover:bg-muted/40 transition-colors">
                                    {row.map((cell, cIdx) => (
                                      <td key={cIdx} className="px-3.5 py-2 font-normal text-foreground/90 border-r last:border-r-0 border-border/30">
                                        {cell}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        );
                      })}
                      {assistantStreaming && isLast && msg.role === "assistant" && (
                        <span className="inline-block w-2.5 h-4 ml-1 bg-primary animate-pulse align-middle rounded-xs" />
                      )}
                    </div>
                  )}
                </>
              );
            })()}

            {/* Human-in-the-Loop Terminal Approval Card */}
            {msg.role === "assistant" && msg.content && (
              (() => {
                const msgText: string = msg.content;
                const hasRequest = msgText.includes("Terminal Execution Request") ||
                  msgText.includes("approval_required") ||
                  msgText.includes("Approve & Execute") ||
                  msgText.includes("Approve!") ||
                  msgText.includes("нужно твоё") ||
                  /gcc\s+|-o\s+|mkdir\s+-p/i.test(msgText);
                if (!hasRequest) return null;

                const codeBlockMatch: RegExpMatchArray | null = msgText.match(/```(?:bash|sh|c)?\n([\s\S]*?)\n```/i);
                const rawCmd = (codeBlockMatch ? codeBlockMatch[1].trim() : null) ||
                  (msgText.match(/(?:Command|Команда):\s*`?([^`\n]+)`?/i)?.[1]?.trim()) ||
                  (msgText.match(/`([^`]+)`/)?.[1]?.trim());

                const isRealCode = rawCmd && !/[а-яА-Я]/.test(rawCmd) && !rawCmd.includes("->");
                const cmd = isRealCode ? rawCmd : "mkdir -p backend/native && gcc -O3 -march=native -o backend/native/process backend/native/process.c -lm && ./backend/native/process";
                const ratMatch = msgText.match(/(?:Rationale|Reason|Причина|Что будет выполнено):\s*([^\n]+)/i);
                const reqIdMatch = msgText.match(/request_id:\s*([a-f0-9\-]+)/i);
                const rationale = ratMatch ? ratMatch[1].trim() : "Execution of native C compilation pipeline in backend/native";
                const requestId = reqIdMatch ? reqIdMatch[1] : null;

                return (
                  <div className="mt-3 p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/5 text-xs font-sans space-y-3 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-semibold text-foreground">
                        <Shield size={15} className="text-amber-500 shrink-0" />
                        <span>Terminal Execution Request</span>
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted/80">Pending Approval</span>
                    </div>
                    <div className="space-y-1 font-mono text-[11px] bg-background/80 p-2.5 rounded-lg border border-border/40">
                      <div><span className="text-muted-foreground select-none">Command:   </span><span className="text-emerald-400 font-semibold">{cmd}</span></div>
                      <div><span className="text-muted-foreground select-none">Rationale: </span><span className="text-foreground/90">{rationale}</span></div>
                    </div>
                    <div className="flex items-center gap-2 pt-0.5">
                      <button
                        onClick={async (e) => {
                          const btn = e.currentTarget;
                          btn.disabled = true;
                          btn.innerText = "Approved & Executing...";
                          btn.className = "px-3.5 py-1.5 rounded-lg bg-emerald-700 text-white font-medium text-xs opacity-80 cursor-wait flex items-center gap-1.5";
                          try {
                            let res: any;
                            if (requestId) {
                              res = await api.post(`/terminal/approval/${requestId}/approve`);
                            } else {
                              res = await api.post(`/terminal/approval/approve_latest`, { command: cmd });
                            }
                            if (res && res.output) {
                              btn.innerText = "Execution Completed ✓";
                              btn.className = "px-3.5 py-1.5 rounded-lg bg-emerald-600 text-white font-medium text-xs flex items-center gap-1.5";
                            }
                          } catch (err) {
                            console.error("Failed to approve terminal execution:", err);
                          }
                        }}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-medium text-xs transition-colors flex items-center gap-1.5 shadow-sm active:scale-95"
                      >
                        <span>Approve & Execute</span>
                      </button>
                    </div>
                  </div>
                );
              })()
            )}

            {/* Autonomous Execution Plan Stepper */}
            {msg.role === "assistant" && msg.content && (
              (() => {
                const text = msg.content;
                const planMatch = text.match(/(?:🎬\s*Autonomous Execution Plan|Autonomous Execution Plan|План выполнения:?|План автономного выполнения:?)[\s\n]*([\s\S]*?)(?=\n\n(?:[#💡💡]|$)|$)/i);
                if (!planMatch) return null;
                const rawSteps = planMatch[1].split("\n").map(l => l.trim()).filter(l => l.length > 0 && /^[-*•\d.✓✅🎬]/.test(l));
                if (rawSteps.length === 0) return null;
                return (
                  <div className="mt-3 p-3 rounded-lg border border-primary/20 bg-primary/5 space-y-2">
                    <p className="text-[12px] font-semibold text-primary flex items-center gap-1.5">
                      <Zap size={14} className="animate-pulse" />
                      <span> (Autonomous Execution Plan):</span>
                    </p>
                    <div className="space-y-1.5 text-xs text-foreground/90">
                      {rawSteps.map((step, idx) => {
                        const isDone = /✓|✅|completed|done/i.test(step);
                        return (
                          <div key={idx} className="flex items-center gap-2">
                            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${isDone ? "bg-emerald-500 text-white" : "bg-primary/20 text-primary"}`}>
                              {isDone ? "✓" : idx + 1}
                            </span>
                            <span className={isDone ? "line-through text-muted-foreground" : "font-medium"}>
                              {step.replace(/^[-*•\d.\s✓✅]+/, "")}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()
            )}

            {/* Interactive Proactive Suggestion Chips */}
            {msg.role === "assistant" && msg.content && (
              (() => {
                const text = msg.content;
                const headerMatch = text.match(/(?:💡\s*Proactive Suggestions|Proactive Suggestions|Что дальше\??(?:\s*Может:?)?|Что предложишь\??|Варианты:?|Дальнейшие шаги:?|Следующие шаги:?)[\s\n]*([\s\S]*?)$/i);
                let targetBlock = headerMatch ? headerMatch[1] : "";

                if (!targetBlock) {
                  const parts = text.trim().split(/\n\n+/);
                  const lastPart = parts[parts.length - 1];
                  if (lastPart && /^[\s]*[-*•\d.🔧🧪📝💡🚀📌❓👉]/m.test(lastPart)) {
                    targetBlock = lastPart;
                  }
                }

                if (!targetBlock) return null;

                const rawLines = targetBlock.split("\n");
                const suggestions: string[] = [];
                for (const line of rawLines) {
                  const trimmed = line.trim();
                  if (!trimmed || trimmed.toLowerCase().startsWith("что дальше")) continue;
                  const cleaned = trimmed
                    .replace(/^[-*•\d.\s]+/, "")
                    .replace(/^(?:🔧|🧪|📝|💡|🚀|📌|❓|👉|✅|🤝)\s*/, "")
                    .trim();
                  if (cleaned.length >= 3 && cleaned.length < 120) {
                    suggestions.push(cleaned);
                  }
                }

                if (suggestions.length === 0) return null;
                return (
                  <div className="mt-3 pt-2.5 border-t border-border/40 space-y-2">
                    <p className="text-[11px] font-bold text-muted-foreground flex items-center gap-1">
                      <Sparkles size={12} className="text-primary" />
                      <span>Suggested Actions (click to select):</span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {suggestions.map((sug, sIdx) => (
                        <button
                          key={sIdx}
                          onClick={() => onSelectSuggestion(sug)}
                          className="text-xs px-3 py-1.5 rounded-xl bg-primary/10 hover:bg-primary/20 border border-primary/20 text-foreground transition-all flex items-center gap-1.5 text-left font-medium shadow-sm hover:scale-[1.01] active:scale-[0.99]"
                        >
                          <Sparkles size={11} className="text-primary shrink-0 opacity-70" />
                          <span>{sug}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })()
            )}
          </div>
        )}

        {/* Assistant Feedback & Copy Action Bar */}
        {msg.role === "assistant" && (
          <div className="flex items-center gap-1 mt-1.5">
            {msg.id && (
              <>
                <button
                  onClick={() => onSendFeedback(msg.id!, "thumbs_up")}
                  aria-label="Good response"
                  className={`p-1.5 rounded-lg transition-all hover:bg-muted ${feedback[msg.id] === "thumbs_up" ? "text-green-500" : "text-muted-foreground"}`}
                  title="Good response"
                >
                  <ThumbsUp size={14} />
                </button>
                <button
                  onClick={() => onSendFeedback(msg.id!, "thumbs_down")}
                  aria-label="Bad response"
                  className={`p-1.5 rounded-lg transition-all hover:bg-muted ${feedback[msg.id] === "thumbs_down" ? "text-red-500" : "text-muted-foreground"}`}
                  title="Bad response"
                >
                  <ThumbsDown size={14} />
                </button>
              </>
            )}
            <button
              onClick={() => {
                const { cleanText } = parseThoughtsAndCleanText(msg.content || "");
                onCopy(cleanText || msg.content || "");
              }}
              aria-label="Copy response"
              className="p-1.5 rounded-lg transition-all hover:bg-muted text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
              title="Copy response"
            >
              {copiedCode === (parseThoughtsAndCleanText(msg.content || "").cleanText || msg.content) ? (
                <Check size={14} className="text-emerald-500" />
              ) : (
                <Copy size={14} />
              )}
            </button>
          </div>
        )}

        {/* User Message Action Bar (Edit & Copy) */}
        {msg.role === "user" && msg.content && (
          <div className="flex items-center gap-1.5 mt-1 justify-end opacity-90 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => onEditPrompt(msg.content)}
              className="px-2 py-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 text-[11px] flex items-center gap-1 transition-colors"
              title="Edit message"
            >
              <Pencil size={12} />
              <span>Edit</span>
            </button>
            <button
              onClick={() => onCopy(msg.content)}
              className="px-2 py-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 text-[11px] flex items-center gap-1 transition-colors"
              title="Copy prompt"
            >
              {copiedCode === msg.content ? (
                <Check size={12} className="text-emerald-500" />
              ) : (
                <Copy size={12} />
              )}
              <span>{copiedCode === msg.content ? "Copied" : "Copy"}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
