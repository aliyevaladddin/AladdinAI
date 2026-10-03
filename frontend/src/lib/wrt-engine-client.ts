// NOTICE: This file is protected under RCF-PL

/**
 * WRT Engine Client — TypeScript wrapper for the native C WRT Engine API.
 *
 * All WRT parsing, validation, serialization, and conversion logic lives in the C engine.
 * This client provides a thin async interface for the frontend to call the C backend
 * via the REST API (with automatic auth token).
 *
 * Error contract: every method throws {@link WrtEngineError} when the engine cannot be
 * reached or answers with a non-2xx status. Failures are never disguised as a successful
 * but empty result — a caller that gets a value back can trust that the engine really
 * produced it. This matters for editing: a silent `""` from fromEditableHtml would blank
 * the user's document.
 */

import { API_URL, authedFetch } from "./api";

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

export interface WrtStats {
  lines: number;
  words: number;
  chars: number;
  tags: number;
  valid: boolean;
}

/**
 * Raised when the native engine is unreachable, errors out, or answers with a
 * non-2xx status.
 *
 * `status` is undefined for transport failures (backend down, DNS, aborted
 * request); `cause` keeps the original error for logging.
 */
export class WrtEngineError extends Error {
  readonly action: string;
  readonly status?: number;

  constructor(action: string, message: string, options?: { status?: number; cause?: unknown }) {
    super(message);
    this.name = "WrtEngineError";
    this.action = action;
    this.status = options?.status;
    if (options?.cause !== undefined) {
      // `cause` is ES2022; assign directly so the lib target stays as-is.
      (this as { cause?: unknown }).cause = options.cause;
    }
  }
}

/**
 * Main client class for calling the native C WRT Engine.
 * All methods are async and handle auth token automatically via authedFetch.
 */
export class WrtEngineClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * POST JSON to the engine and parse the JSON reply.
   *
   * Every failure mode — non-2xx, unparseable body, network error — becomes a
   * WrtEngineError so that callers never receive a fabricated empty result.
   */
  private async postJson<T>(action: string, path: string, body: Record<string, unknown>): Promise<T> {
    let res: Response;
    try {
      res = await authedFetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (err) {
      throw new WrtEngineError(action, `Native engine unreachable while running "${action}"`, {
        cause: err,
      });
    }

    if (!res.ok) {
      throw new WrtEngineError(action, `Native engine failed "${action}" (HTTP ${res.status} ${res.statusText})`, {
        status: res.status,
      });
    }

    let data: T;
    try {
      data = (await res.json()) as T;
    } catch (err) {
      throw new WrtEngineError(action, `Native engine returned malformed JSON for "${action}"`, {
        status: res.status,
        cause: err,
      });
    }

    if (data && typeof data === "object" && "success" in data && (data as { success?: unknown }).success === false) {
      const detail = (data as { error?: string }).error || "no detail";
      throw new WrtEngineError(action, `Native engine reported failure for "${action}": ${detail}`);
    }

    return data;
  }

  /**
   * Validate WRT document using native C engine.
   * Returns detailed validation report with issues.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails. A report is
   *   never synthesised locally — callers decide on their own fallback.
   */
  async validate(content: string): Promise<WrtValidationReport> {
    const data = await this.postJson<WrtValidationReport>("validate", "/wrt/validate", { content });
    if (typeof data.valid !== "boolean") {
      throw new WrtEngineError("validate", "Native engine returned a validation report without a 'valid' field");
    }
    return { ...data, issues: data.issues ?? [] };
  }

  /**
   * Auto-fix WRT document tags (close unclosed tags, remove empty brackets).
   * Returns corrected WRT text.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails. The input is
   *   never echoed back as if it had been fixed.
   */
  async fix(content: string): Promise<string> {
    const data = await this.postJson<{ content?: string }>("fix", "/wrt/fix", { content });
    if (typeof data.content !== "string") {
      throw new WrtEngineError("fix", "Native engine returned a fix response without a 'content' field");
    }
    return data.content;
  }

  /**
   * Convert WRT to styled HTML for display (non-editable).
   * Used for preview/rendering purposes.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails.
   */
  async toHtml(content: string): Promise<string> {
    const data = await this.postJson<{ html?: string }>("to-html", "/wrt/to-html", { content });
    if (typeof data.html !== "string") {
      throw new WrtEngineError("to-html", "Native engine returned an HTML response without a 'html' field");
    }
    return data.html;
  }

  /**
   * Convert WRT to editable HTML for contentEditable WYSIWYG mode.
   * This is the primary method for Visual Mode rendering.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails. An empty
   *   paragraph is NOT substituted: rendering one would show a blank editor and
   *   invite the user to type into a document that is about to be overwritten.
   */
  async toEditableHtml(content: string): Promise<string> {
    const data = await this.postJson<{ html?: string }>(
      "to-editable-html",
      "/wrt/to-editable-html",
      { content }
    );
    if (typeof data.html !== "string") {
      throw new WrtEngineError("to-editable-html", "Native engine returned an HTML response without a 'html' field");
    }
    return data.html;
  }

  /**
   * Convert editable HTML from contentEditable back to canonical WRT.
   * This is the primary method for Visual Mode serialization on save/switch.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails. Returning ""
   *   here would erase the open document on the very next keystroke.
   */
  async fromEditableHtml(html: string): Promise<string> {
    const data = await this.postJson<{ content?: string }>(
      "from-editable-html",
      "/wrt/from-editable-html",
      { content: html }
    );
    if (typeof data.content !== "string") {
      throw new WrtEngineError("from-editable-html", "Native engine returned a WRT response without a 'content' field");
    }
    return data.content;
  }

  /**
   * Get document statistics (lines, words, chars, tags).
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails.
   */
  async stats(content: string): Promise<WrtStats> {
    const data = await this.postJson<WrtStats>("stats", "/wrt/stats", { content });
    if (typeof data.lines !== "number" || typeof data.words !== "number") {
      throw new WrtEngineError("stats", "Native engine returned a stats response missing numeric fields");
    }
    return data;
  }

  /**
   * List files in workspace directory.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails. An empty
   *   listing is reported as "no files", which would hide the outage from the user.
   */
  async listFiles(dirPath?: string): Promise<{ path: string; files: WrtFileEntry[] }> {
    const action = "list-files";
    const url = dirPath
      ? `${this.baseUrl}/wrt/files?path=${encodeURIComponent(dirPath)}`
      : `${this.baseUrl}/wrt/files`;

    let res: Response;
    try {
      res = await authedFetch(url);
    } catch (err) {
      throw new WrtEngineError(action, "Native engine unreachable while listing files", { cause: err });
    }
    if (!res.ok) {
      throw new WrtEngineError(action, `Native engine failed to list files (HTTP ${res.status} ${res.statusText})`, {
        status: res.status,
      });
    }

    let data: { path?: string; files?: WrtFileEntry[] };
    try {
      data = await res.json();
    } catch (err) {
      throw new WrtEngineError(action, "Native engine returned malformed JSON while listing files", {
        status: res.status,
        cause: err,
      });
    }

    if (!Array.isArray(data.files)) {
      throw new WrtEngineError(action, "Native engine returned a file listing without a 'files' array");
    }
    return { path: data.path ?? "", files: data.files };
  }

  /**
   * Read file content from workspace.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails.
   */
  async readFile(filePath: string): Promise<{ content: string; lines: number; size: number }> {
    let res: Response;
    try {
      res = await authedFetch(`${this.baseUrl}/wrt/files/read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filePath }),
      });
    } catch (err) {
      throw new WrtEngineError("read-file", "Native engine unreachable while reading the file", { cause: err });
    }
    if (!res.ok) {
      throw new WrtEngineError("read-file", `Failed to read file: ${res.status} ${res.statusText}`, {
        status: res.status,
      });
    }
    const data = await res.json();
    if (data.success === false) {
      throw new WrtEngineError("read-file", data.error || "Cannot read file");
    }
    return { content: data.content ?? "", lines: data.lines ?? 1, size: data.size ?? 0 };
  }

  /**
   * Save file content to workspace.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails.
   */
  async saveFile(filePath: string, content: string): Promise<{ success: boolean; bytes_written: number }> {
    let res: Response;
    try {
      res = await authedFetch(`${this.baseUrl}/wrt/files/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filePath, content }),
      });
    } catch (err) {
      throw new WrtEngineError("save-file", "Native engine unreachable while saving the file", { cause: err });
    }
    if (!res.ok) {
      throw new WrtEngineError("save-file", `Failed to save file: ${res.status} ${res.statusText}`, {
        status: res.status,
      });
    }
    const data = await res.json();
    if (data.success === false) {
      throw new WrtEngineError("save-file", data.error || "Cannot save file");
    }
    return { success: true, bytes_written: data.bytes_written ?? 0 };
  }

  /**
   * Get list of recently edited files.
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails. Returns null
   *   for "recent list unavailable" callers that treat it as optional.
   */
  async getRecentFiles(): Promise<WrtRecentFile[]> {
    let res: Response;
    try {
      res = await authedFetch(`${this.baseUrl}/wrt/files/recent`);
    } catch (err) {
      throw new WrtEngineError("recent-files", "Native engine unreachable while reading recent files", { cause: err });
    }
    if (!res.ok) {
      throw new WrtEngineError("recent-files", `Failed to read recent files (HTTP ${res.status} ${res.statusText})`, {
        status: res.status,
      });
    }
    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  }

  /**
   * Export WRT document to various formats (docx, odt, pptx, md, wrt).
   *
   * @throws {WrtEngineError} when the engine is unreachable or fails.
   */
  async export(
    content: string,
    filename?: string,
    format: "docx" | "odt" | "pptx" | "md" | "wrt" = "docx"
  ): Promise<void> {
    let res: Response;
    try {
      res = await authedFetch(`${this.baseUrl}/wrt/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, filename, format }),
      });
    } catch (err) {
      throw new WrtEngineError("export", "Native engine unreachable while exporting the document", { cause: err });
    }
    if (!res.ok) {
      throw new WrtEngineError("export", `Export failed (${res.status})`, { status: res.status });
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

  /**
   * Convert an office or markdown file into WRT for the editor.
   *
   * The file is sent as raw bytes rather than base64 JSON: a .pptx with embedded
   * media is tens of megabytes, and base64 would inflate it by a third and cost
   * a decode on the way in. The format is carried in the `filename` query
   * parameter because browsers set Content-Type inconsistently for Office
   * files -- several send application/octet-stream.
   *
   * @throws {WrtEngineError} when the engine is unreachable, the format is
   * unsupported (415), the file is empty (400) or corrupt (422).
   */
  async importDocument(file: File): Promise<{ content: string; filename: string }> {
    const action = "import";
    let res: Response;
    try {
      res = await authedFetch(
        `${this.baseUrl}/wrt/import?filename=${encodeURIComponent(file.name)}`,
        { method: "POST", body: file }
      );
    } catch (err) {
      throw new WrtEngineError(action, "Native engine unreachable while importing the file", { cause: err });
    }
    if (!res.ok) {
      // The backend's detail is written for the user who dropped the file, so
      // prefer it over a bare status code: "this file is corrupt" and "this
      // format is not supported" call for different reactions.
      let detail = `Import failed (${res.status})`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        // A non-JSON error body is not worth failing over; keep the status.
      }
      throw new WrtEngineError(action, detail, { status: res.status });
    }
    const data = await res.json();
    if (typeof data?.content !== "string") {
      throw new WrtEngineError(action, "Native engine returned an import response without a 'content' field");
    }
    return { content: data.content, filename: typeof data.filename === "string" ? data.filename : `${file.name}.wrt` };
  }
}

/**
 * Singleton instance for convenient imports.
 * Use `wrtClient` for most cases.
 */
export const wrtClient = new WrtEngineClient();