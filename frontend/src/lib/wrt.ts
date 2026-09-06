// NOTICE: This file is protected under RCF-PL

/**
 * Browser-side WRT presentation and serialization helpers.
 *
 * WRT remains the canonical document format used by the Workspace and agents.
 * These helpers give people a visual authoring surface without exposing its
 * semantic tags while retaining a predictable route back to WRT on save.
 */

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
