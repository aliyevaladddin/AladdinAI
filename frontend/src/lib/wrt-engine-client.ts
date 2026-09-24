// NOTICE: This file is protected under RCF-PL

/**
 * WRT Engine Client — TypeScript wrapper for the native C WRT Engine API.
 *
 * All WRT parsing, validation, serialization, and conversion logic lives in the C engine.
 * This client provides a thin async interface for the frontend to call the C backend
 * via the REST API (with automatic auth token).
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
 * Main client class for calling the native C WRT Engine.
 * All methods are async and handle auth token automatically via authedFetch.
 */
export class WrtEngineClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Validate WRT document using native C engine.
   * Returns detailed validation report with issues.
   */
  async validate(content: string): Promise<WrtValidationReport> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.debug("[WrtEngineClient] validate failed:", err);
    }
    // Fallback: assume valid
    return { valid: true, word_count: 0, char_count: content.length, line_count: 1, tag_count: 0, issues: [] };
  }

  /**
   * Auto-fix WRT document tags (close unclosed tags, remove empty brackets).
   * Returns corrected WRT text.
   */
  async fix(content: string): Promise<string> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/fix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        const data = await res.json();
        return data.content ?? content;
      }
    } catch (err) {
      console.debug("[WrtEngineClient] fix failed:", err);
    }
    return content;
  }

  /**
   * Convert WRT to styled HTML for display (non-editable).
   * Used for preview/rendering purposes.
   */
  async toHtml(content: string): Promise<string> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/to-html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        const data = await res.json();
        return data.html ?? "";
      }
    } catch (err) {
      console.debug("[WrtEngineClient] toHtml failed:", err);
    }
    return "";
  }

  /**
   * Convert WRT to editable HTML for contentEditable WYSIWYG mode.
   * Ensures non-empty output with proper caret positioning.
   * This is the primary method for Visual Mode rendering.
   */
  async toEditableHtml(content: string): Promise<string> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/to-editable-html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        const data = await res.json();
        return data.html ?? "<p><br></p>";
      }
    } catch (err) {
      console.debug("[WrtEngineClient] toEditableHtml failed:", err);
    }
    return "<p><br></p>";
  }

  /**
   * Convert editable HTML from contentEditable back to canonical WRT.
   * This is the primary method for Visual Mode serialization on save/switch.
   */
  async fromEditableHtml(html: string): Promise<string> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/from-editable-html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: html }),
      });
      if (res.ok) {
        const data = await res.json();
        return data.content ?? "";
      }
    } catch (err) {
      console.debug("[WrtEngineClient] fromEditableHtml failed:", err);
    }
    return "";
  }

  /**
   * Get document statistics (lines, words, chars, tags).
   */
  async stats(content: string): Promise<WrtStats> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/stats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.debug("[WrtEngineClient] stats failed:", err);
    }
    return { lines: 0, words: 0, chars: content.length, tags: 0, valid: true };
  }

  /**
   * List files in workspace directory.
   */
  async listFiles(dirPath?: string): Promise<{ path: string; files: WrtFileEntry[] }> {
    try {
      const url = dirPath
        ? `${this.baseUrl}/wrt/files?path=${encodeURIComponent(dirPath)}`
        : `${this.baseUrl}/wrt/files`;
      const res = await authedFetch(url);
      if (res.ok) {
        const data = await res.json();
        return { path: data.path || "", files: data.files || [] };
      }
    } catch (err) {
      console.debug("[WrtEngineClient] listFiles failed:", err);
    }
    return { path: "", files: [] };
  }

  /**
   * Read file content from workspace.
   */
  async readFile(filePath: string): Promise<{ content: string; lines: number; size: number }> {
    const res = await authedFetch(`${this.baseUrl}/wrt/files/read`, {
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

  /**
   * Save file content to workspace.
   */
  async saveFile(filePath: string, content: string): Promise<{ success: boolean; bytes_written: number }> {
    const res = await authedFetch(`${this.baseUrl}/wrt/files/save`, {
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

  /**
   * Get list of recently edited files.
   */
  async getRecentFiles(): Promise<WrtRecentFile[]> {
    try {
      const res = await authedFetch(`${this.baseUrl}/wrt/files/recent`);
      if (res.ok) {
        const data = await res.json();
        return data.files || [];
      }
    } catch (err) {
      console.debug("[WrtEngineClient] getRecentFiles failed:", err);
    }
    return [];
  }

  /**
   * Export WRT document to various formats (docx, odt, pptx, md, wrt).
   */
  async export(
    content: string,
    filename?: string,
    format: "docx" | "odt" | "pptx" | "md" | "wrt" = "docx"
  ): Promise<void> {
    const res = await authedFetch(`${this.baseUrl}/wrt/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
}

/**
 * Singleton instance for convenient imports.
 * Use `wrtClient` for most cases.
 */
export const wrtClient = new WrtEngineClient();