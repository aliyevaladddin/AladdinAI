// NOTICE: This file is protected under RCF-PL

/**
 * Browser-side WRT presentation and serialization helpers.
 *
 * WRT remains the canonical document format used by the Workspace and agents.
 * These helpers give people a visual authoring surface without exposing its
 * semantic tags while retaining a predictable route back to WRT on save.
 */

import { API_URL } from "./api";

const INLINE_TAGS: Record<string, string> = {
  b: "strong",
  i: "em",
  u: "u",
  s: "s",
  code: "code",
};

const BLOCK_TAGS = new Set(["h1", "h2", "h3", "quote"]);
const SUPPORTED_TAGS = new Set([...Object.keys(INLINE_TAGS), ...BLOCK_TAGS]);

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeWrtText(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\[/g, "\\[");
}

function unescapeWrtText(value: string): string {
  return value.replace(/\\\[/g, "[").replace(/\\\\/g, "\\");
}

function safeImageSource(source: string): string | null {
  const trimmed = source.trim();
  if (
    trimmed.startsWith("/") ||
    /^https?:\/\//i.test(trimmed) ||
    /^data:image\/(?:png|jpe?g|gif|bmp|webp);base64,/i.test(trimmed)
  ) {
    return trimmed;
  }
  return null;
}

function findTagClose(input: string, tag: string, from: number): number {
  const token = new RegExp(`\\[(/?)${tag}\\]`, "g");
  token.lastIndex = from;
  let depth = 1;
  let match: RegExpExecArray | null;

  while ((match = token.exec(input)) !== null) {
    if (match[1] === "/") {
      depth -= 1;
      if (depth === 0) return match.index;
    } else {
      depth += 1;
    }
  }
  return -1;
}

function renderInlineWrt(input: string): string {
  const openingTag = /\[([a-z0-9]+)\]/gi;
  let cursor = 0;
  let html = "";
  let match: RegExpExecArray | null;

  while ((match = openingTag.exec(input)) !== null) {
    const tag = match[1].toLowerCase();
    const isEscaped = match.index > 0 && input[match.index - 1] === "\\";
    if (isEscaped || !SUPPORTED_TAGS.has(tag)) continue;

    const closeStart = findTagClose(input, tag, openingTag.lastIndex);
    if (closeStart === -1) continue;

    html += escapeHtml(unescapeWrtText(input.slice(cursor, match.index)));
    const innerStart = openingTag.lastIndex;
    const inner = input.slice(innerStart, closeStart);
    const element = INLINE_TAGS[tag] ?? (tag === "quote" ? "blockquote" : tag);
    html += `<${element}>${renderInlineWrt(inner)}</${element}>`;

    const closeEnd = closeStart + tag.length + 3;
    cursor = closeEnd;
    openingTag.lastIndex = closeEnd;
  }

  html += escapeHtml(unescapeWrtText(input.slice(cursor)));
  return html;
}

function tableToHtml(lines: string[]): string {
  const rows = lines
    .filter((line) => line.trim().startsWith("|"))
    .map((line) =>
      line
        .trim()
        .split("|")
        .slice(1, -1)
        .map((cell) => cell.trim().replace(/\\\|/g, "|")),
    );

  if (rows.length === 0) return "";

  const [header, ...body] = rows;
  const head = `<thead><tr>${header.map((cell) => `<th>${renderInlineWrt(cell)}</th>`).join("")}</tr></thead>`;
  const bodyRows = body
    .map((cells) => `<tr>${cells.map((cell) => `<td>${renderInlineWrt(cell)}</td>`).join("")}</tr>`)
    .join("");
  return `<table>${head}${bodyRows ? `<tbody>${bodyRows}</tbody>` : ""}</table>`;
}

function imageToHtml(line: string): string | null {
  const match = /^\[img\s+src="([^"]*)"\s+alt="([^"]*)"\]$/i.exec(line.trim());
  if (!match) return null;
  const source = safeImageSource(match[1]);
  if (!source) return null;
  return `<img src="${escapeHtml(source)}" alt="${escapeHtml(match[2])}">`;
}

/** Render WRT as safe semantic HTML. It never executes document markup. */
export function wrtToHtml(wrt: string): string {
  const lines = wrt.replace(/\r\n?/g, "\n").split("\n");
  const blocks: string[] = [];
  let paragraph: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    blocks.push(`<p>${paragraph.map(renderInlineWrt).join("<br>")}</p>`);
    paragraph = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const image = imageToHtml(line);
    if (image) {
      flushParagraph();
      blocks.push(image);
      continue;
    }

    const heading = /^\[(h[1-3])\]([\s\S]*)\[\/\1\]$/i.exec(line.trim());
    if (heading) {
      flushParagraph();
      blocks.push(`<${heading[1].toLowerCase()}>${renderInlineWrt(heading[2])}</${heading[1].toLowerCase()}>`);
      continue;
    }

    if (line.trim() === "[quote]") {
      flushParagraph();
      const quoteLines: string[] = [];
      index += 1;
      while (index < lines.length && lines[index].trim() !== "[/quote]") {
        quoteLines.push(lines[index]);
        index += 1;
      }
      blocks.push(`<blockquote>${quoteLines.map(renderInlineWrt).join("<br>")}</blockquote>`);
      continue;
    }

    if (line.trim() === "[list]") {
      flushParagraph();
      const items: string[] = [];
      index += 1;
      while (index < lines.length && lines[index].trim() !== "[/list]") {
        const item = /^\*\s?(.*)$/.exec(lines[index].trim());
        if (item) items.push(`<li>${renderInlineWrt(item[1])}</li>`);
        index += 1;
      }
      blocks.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    if (line.trim() === "[table]") {
      flushParagraph();
      const tableLines: string[] = [];
      index += 1;
      while (index < lines.length && lines[index].trim() !== "[/table]") {
        tableLines.push(lines[index]);
        index += 1;
      }
      blocks.push(tableToHtml(tableLines));
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      continue;
    }

    paragraph.push(line);
  }

  flushParagraph();
  return blocks.join("\n");
}

function childNodesToWrt(node: Element): string {
  let output = "";
  node.childNodes.forEach((child) => {
    if (child.nodeType === 3) {
      output += escapeWrtText(child.textContent ?? "");
      return;
    }
    if (child.nodeType !== 1) return;

    const element = child as HTMLElement;
    const tag = element.tagName.toLowerCase();
    if (tag === "br") {
      output += "\n";
      return;
    }
    if (tag === "img") {
      const source = safeImageSource(element.getAttribute("src") ?? "");
      const alt = (element.getAttribute("alt") ?? "image").replace(/"/g, "'");
      if (source) output += `[img src="${source}" alt="${alt}"]`;
      return;
    }

    const inner = childNodesToWrt(element);
    switch (tag) {
      case "strong":
      case "b":
        output += `[b]${inner}[/b]`;
        break;
      case "em":
      case "i":
        output += `[i]${inner}[/i]`;
        break;
      case "u":
        output += `[u]${inner}[/u]`;
        break;
      case "s":
      case "strike":
      case "del":
        output += `[s]${inner}[/s]`;
        break;
      case "code":
        output += `[code]${inner}[/code]`;
        break;
      default:
        output += inner;
    }
  });
  return output;
}

function tableToWrt(table: HTMLTableElement): string {
  const rows = Array.from(table.rows).map((row) => {
    const cells = Array.from(row.cells).map((cell) =>
      childNodesToWrt(cell).replace(/\\/g, "\\\\").replace(/\|/g, "\\|"),
    );
    return `| ${cells.join(" | ")} |`;
  });
  return `[table]\n${rows.join("\n")}\n[/table]`;
}

function blockToWrt(element: Element): string {
  const tag = element.tagName.toLowerCase();
  const content = childNodesToWrt(element).trimEnd();

  if (/^h[1-3]$/.test(tag)) return `[${tag}]${content}[/${tag}]`;
  if (tag === "blockquote") return `[quote]\n${content}\n[/quote]`;
  if (tag === "ul" || tag === "ol") {
    const items = Array.from(element.children)
      .filter((child) => child.tagName.toLowerCase() === "li")
      .map((item) => `* ${childNodesToWrt(item).trim()}`);
    return `[list]\n${items.join("\n")}\n[/list]`;
  }
  if (tag === "table") return tableToWrt(element as HTMLTableElement);
  if (tag === "img") {
    const source = safeImageSource((element as HTMLElement).getAttribute("src") ?? "");
    const alt = ((element as HTMLElement).getAttribute("alt") ?? "image").replace(/"/g, "'");
    return source ? `[img src="${source}" alt="${alt}"]` : "";
  }
  if (tag === "pre") return `[code]${content}[/code]`;
  return content;
}

/** Serialize a contentEditable WRT document back into canonical WRT text. */
export function editableElementToWrt(root: HTMLElement): string {
  const blocks: string[] = [];
  let inlineBuffer = "";

  const flushInline = () => {
    const value = inlineBuffer.trimEnd();
    if (value) blocks.push(value);
    inlineBuffer = "";
  };

  root.childNodes.forEach((child) => {
    if (child.nodeType === 3) {
      inlineBuffer += escapeWrtText(child.textContent ?? "");
      return;
    }
    if (child.nodeType !== 1) return;

    const element = child as HTMLElement;
    const tag = element.tagName.toLowerCase();
    if (["p", "div", "h1", "h2", "h3", "blockquote", "ul", "ol", "table", "pre", "img"].includes(tag)) {
      flushInline();
      const block = blockToWrt(element);
      if (block) blocks.push(block);
      return;
    }
    inlineBuffer += childNodesToWrt(element);
  });

  flushInline();
  return blocks.join("\n\n").replace(/\n{3,}/g, "\n\n").trimEnd() + (blocks.length ? "\n" : "");
}

/** A presentation-ready editable document. Empty documents keep a visible caret line. */
export function wrtToEditableHtml(wrt: string): string {
  return wrtToHtml(wrt) || "<p><br></p>";
}

/* ── Native C Engine API helpers ─────────────────────────────────── */

export interface WrtIssue {
  line: number;
  col: number;
  tag: string;
  message: string;
  severity: number;
}

export interface WrtValidationReport {
  valid: boolean;
  word_count: number;
  char_count: number;
  line_count: number;
  tag_count: number;
  issues: WrtIssue[];
}

export async function validateWrtNative(content: string): Promise<WrtValidationReport> {
  try {
    const res = await fetch(`${API_URL}/wrt/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.debug("Native C validation fallback:", err);
  }
  return { valid: true, word_count: 0, char_count: content.length, line_count: 1, tag_count: 0, issues: [] };
}

export async function fixWrtNative(content: string): Promise<string> {
  try {
    const res = await fetch(`${API_URL}/wrt/fix`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (res.ok) {
      const data = await res.json();
      return data.content ?? content;
    }
  } catch (err) {
    console.debug("Native C fix fallback:", err);
  }
  return content;
}

export interface WrtFileEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  mtime: number;
  ext: string;
}

export interface WrtRecentFile {
  name: string;
  path: string;
  exists: boolean;
  size: number;
  mtime: number;
}

export async function listWrtFilesNative(dirPath?: string): Promise<{ path: string; files: WrtFileEntry[] }> {
  try {
    const url = dirPath ? `${API_URL}/wrt/files?path=${encodeURIComponent(dirPath)}` : `${API_URL}/wrt/files`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      return { path: data.path || "", files: data.files || [] };
    }
  } catch (err) {
    console.debug("Failed to list files via Native C engine:", err);
  }
  return { path: "", files: [] };
}

export async function readWrtFileNative(filePath: string): Promise<{ content: string; lines: number; size: number }> {
  const res = await fetch(`${API_URL}/wrt/files/read`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: filePath }),
  });
  if (!res.ok) {
    throw new Error(`Failed to read file: ${res.statusText}`);
  }
  const data = await res.json();
  if (!data.success) {
    throw new Error(data.error || "Cannot read file");
  }
  return { content: data.content || "", lines: data.lines || 1, size: data.size || 0 };
}

export async function saveWrtFileNative(filePath: string, content: string): Promise<{ success: boolean; bytes_written: number }> {
  const res = await fetch(`${API_URL}/wrt/files/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: filePath, content }),
  });
  if (!res.ok) {
    throw new Error(`Failed to save file: ${res.statusText}`);
  }
  const data = await res.json();
  if (!data.success) {
    throw new Error(data.error || "Cannot save file");
  }
  return { success: true, bytes_written: data.bytes_written || 0 };
}

export async function getRecentWrtFilesNative(): Promise<WrtRecentFile[]> {
  try {
    const res = await fetch(`${API_URL}/wrt/files/recent`);
    if (res.ok) {
      const data = await res.json();
      return data.files || [];
    }
  } catch (err) {
    console.debug("Failed to get recent files via Native C engine:", err);
  }
  return [];
}

export async function downloadWrtAsDocument(
  content: string,
  filename?: string,
  format: "docx" | "odt" | "pptx" | "md" | "wrt" = "docx",
): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${API_URL}/wrt/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content, filename, format }),
  });
  if (!res.ok) {
    throw new Error(`Export failed (${res.status})`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const baseName = filename ? filename.replace(/\.[^/.]+$/, "") : "document";
  const defaultName = `${baseName}.${format}`;
  const downloadName = match?.[1] ?? defaultName;

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = downloadName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}



