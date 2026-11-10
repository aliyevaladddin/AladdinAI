// NOTICE: This file is protected under RCF-PL
"use client";

/**
 * Serve Monaco from the installed `monaco-editor` package instead of the
 * jsdelivr CDN that `@monaco-editor/react` downloads by default.
 *
 * Every origin keeps its own browser cache, so a LAN address such as
 * http://192.168.0.x:3000 pays for the whole CDN download again even when
 * http://localhost:3000 already has it cached. When that download is slow the
 * editor's pending work is canceled, which surfaces as `Canceled: Canceled`
 * unhandled rejections, and an offline install has no editor at all.
 *
 * Import this module dynamically from the browser (it touches `window` and
 * `new Worker`) and await it before the first render of `<Editor>`.
 */
import * as monaco from "monaco-editor";
import { loader } from "@monaco-editor/react";

declare global {
  interface Window {
    MonacoEnvironment?: monaco.Environment;
  }
}

// Monaco's editor core runs in a worker; without this it complains and falls
// back to tokenizing on the main thread. Turbopack resolves `new URL(...)`
// against the filesystem only, so the worker is addressed through
// node_modules rather than by its bare package specifier.
window.MonacoEnvironment = {
  getWorker() {
    return new Worker(
      new URL(
        "../../node_modules/monaco-editor/esm/vs/editor/editor.worker.js",
        import.meta.url,
      ),
      { type: "module" },
    );
  },
};

loader.config({ monaco });
