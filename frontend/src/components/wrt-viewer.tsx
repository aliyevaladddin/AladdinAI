"use client";

/**
 * WRT Viewer — renders .wrt tagged text as styled HTML.
 *
 * .wrt tags: [h1]...[/h1] [b]...[/b] [i]...[/i] [u]...[/u] [s]...[/s]
 *            [code]...[/code] [quote]...[/quote] [list]...[/list]
 *            [table]...[/table] [img alt="..."]
 */

import { useMemo } from "react";

interface WrtViewerProps {
  content: string;
  className?: string;
}

/** Escape HTML special chars to prevent XSS from file content. */
function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Render inline .wrt tags to HTML. */
function renderInline(text: string): string {
  let out = esc(text);

  // Bold: [b]...[/b]
  out = out.replace(/\[b\](.*?)\[\/b\]/g, "<strong>$1</strong>");
  // Italic: [i]...[/i]
  out = out.replace(/\[i\](.*?)\[\/i\]/g, "<em>$1</em>");
  // Underline: [u]...[/u]
  out = out.replace(/\[u\](.*?)\[\/u\]/g, "<u>$1</u>");
  // Strikethrough: [s]...[/s]
  out = out.replace(/\[s\](.*?)\[\/s\]/g, "<del>$1</del>");
  // Code: [code]...[/code]
  out = out.replace(
    /\[code\](.*?)\[\/code\]/g,
    '<code class="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">$1</code>',
  );

  return out;
}

/** Parse a .wrt string into HTML blocks. */
function wrtToHtml(wrt: string): string {
  const lines = wrt.split("\n");
  const blocks: string[] = [];
  let inList = false;
  let inTable = false;
  let tableRows: string[][] = [];

  const flushTable = () => {
    if (tableRows.length === 0) return;
    let html = '<div class="overflow-x-auto my-3"><table class="border-collapse text-sm">';
    tableRows.forEach((row, ri) => {
      const tag = ri === 0 ? "th" : "td";
      html += "<tr>";
      row.forEach((cell) => {
        html += `<${tag} class="border border-border px-3 py-1.5 text-left">${renderInline(cell)}</${tag}>`;
      });
      html += "</tr>";
    });
    html += "</table></div>";
    blocks.push(html);
    tableRows = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();

    // Heading
    const headingMatch = trimmed.match(/^\[h([1-3])\](.*?)\[\/h\1\]$/);
    if (headingMatch) {
      if (inList) {
        blocks.push("</ul>");
        inList = false;
      }
      const level = parseInt(headingMatch[1]);
      const text = renderInline(headingMatch[2]);
      const cls =
        level === 1
          ? "text-2xl font-bold mt-6 mb-3"
          : level === 2
            ? "text-xl font-semibold mt-5 mb-2"
            : "text-lg font-medium mt-4 mb-2";
      blocks.push(`<h${level} class="${cls}">${text}</h${level}>`);
      continue;
    }

    // Block quote
    if (trimmed.startsWith("[quote]") && trimmed.endsWith("[/quote]")) {
      const inner = renderInline(trimmed.slice(7, -8));
      blocks.push(
        `<blockquote class="border-l-4 border-primary/30 pl-4 py-1 my-3 italic text-muted-foreground">${inner}</blockquote>`,
      );
      continue;
    }

    // List start/end
    if (trimmed === "[list]") {
      if (inTable) {
        flushTable();
        inTable = false;
      }
      blocks.push('<ul class="list-disc list-inside space-y-1 my-2 pl-2">');
      inList = true;
      continue;
    }
    if (trimmed === "[/list]") {
      blocks.push("</ul>");
      inList = false;
      continue;
    }

    // List item
    if (inList && trimmed.startsWith("* ")) {
      blocks.push(`<li>${renderInline(trimmed.slice(2))}</li>`);
      continue;
    }

    // Table start/end
    if (trimmed === "[table]") {
      if (inList) {
        blocks.push("</ul>");
        inList = false;
      }
      inTable = true;
      continue;
    }
    if (trimmed === "[/table]") {
      flushTable();
      inTable = false;
      continue;
    }

    // Table row
    if (inTable && trimmed.startsWith("|")) {
      const cells = trimmed
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim().replace(/\\|/g, "|"));
      tableRows.push(cells);
      continue;
    }

    // Empty line = paragraph break
    if (!trimmed) {
      if (inList) {
        blocks.push("</ul>");
        inList = false;
      }
      continue;
    }

    // Regular paragraph
    blocks.push(`<p class="my-2 leading-relaxed">${renderInline(trimmed)}</p>`);
  }

  if (inList) blocks.push("</ul>");
  if (inTable) flushTable();

  return blocks.join("\n");
}

export function WrtViewer({ content, className }: WrtViewerProps) {
  const html = useMemo(() => wrtToHtml(content), [content]);

  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-none ${className ?? ""}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/**
 * Detect if a string looks like .wrt format (has at least one .wrt tag).
 */
export function isWrtContent(text: string): boolean {
  return /\[(?:h[1-3]|b|i|u|s|code|quote|list|table|img)\]/.test(text);
}
