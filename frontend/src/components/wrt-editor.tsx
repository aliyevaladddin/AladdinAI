// NOTICE: This file is protected under RCF-PL
"use client";

/**
 * WRT Editor — Monaco-based editor for .wrt tagged text format.
 *
 * Provides syntax highlighting and basic validation for .wrt tags:
 * [h1]...[/h1] [b]...[/b] [i]...[/i] [u]...[/u] [s]...[/s]
 * [code]...[/code] [quote]...[/quote] [list]...[/list] [table]...[/table]
 */

import { useEffect, useRef, useState } from "react";
import Editor, { type Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";

interface WrtEditorProps {
  content: string;
  onChange?: (value: string) => void;
  onSave?: (value: string) => void;
  readOnly?: boolean;
  className?: string;
}

/**
 * Register .wrt language with Monaco for syntax highlighting
 */
function registerWrtLanguage(monaco: Monaco) {
  // Only register once
  if (monaco.languages.getLanguages().some((lang: { id: string }) => lang.id === "wrt")) {
    return;
  }

  monaco.languages.register({ id: "wrt" });

  monaco.languages.setMonarchTokensProvider("wrt", {
    tokenizer: {
      root: [
        // Heading tags
        [/\[h[123]\]/, "tag.heading.open"],
        [/\[\/h[123]\]/, "tag.heading.close"],

        // Inline formatting tags
        [/\[(b|i|u|s|code)\]/, "tag.inline.open"],
        [/\[\/(b|i|u|s|code)\]/, "tag.inline.close"],

        // Block tags
        [/\[(quote|list|table)\]/, "tag.block.open"],
        [/\[\/(quote|list|table)\]/, "tag.block.close"],

        // Image tag
        [/\[img\s+alt="[^"]*"\]/, "tag.image"],

        // List items
        [/^\*\s+/, "list.item"],

        // Table rows
        [/^\|.*\|$/, "table.row"],
      ],
    },
  });

  // Define theme colors for .wrt tags
  monaco.editor.defineTheme("wrt-light", {
    base: "vs",
    inherit: true,
    rules: [
      { token: "tag.heading.open", foreground: "0000FF", fontStyle: "bold" },
      { token: "tag.heading.close", foreground: "0000FF", fontStyle: "bold" },
      { token: "tag.inline.open", foreground: "008800" },
      { token: "tag.inline.close", foreground: "008800" },
      { token: "tag.block.open", foreground: "880088", fontStyle: "bold" },
      { token: "tag.block.close", foreground: "880088", fontStyle: "bold" },
      { token: "tag.image", foreground: "FF8800" },
      { token: "list.item", foreground: "666666", fontStyle: "bold" },
      { token: "table.row", foreground: "666666" },
    ],
    colors: {},
  });

  monaco.editor.defineTheme("wrt-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "tag.heading.open", foreground: "569CD6", fontStyle: "bold" },
      { token: "tag.heading.close", foreground: "569CD6", fontStyle: "bold" },
      { token: "tag.inline.open", foreground: "4EC9B0" },
      { token: "tag.inline.close", foreground: "4EC9B0" },
      { token: "tag.block.open", foreground: "C586C0", fontStyle: "bold" },
      { token: "tag.block.close", foreground: "C586C0", fontStyle: "bold" },
      { token: "tag.image", foreground: "CE9178" },
      { token: "list.item", foreground: "9CDCFE", fontStyle: "bold" },
      { token: "table.row", foreground: "9CDCFE" },
    ],
    colors: {},
  });
}

export function WrtEditor({
  content,
  onChange,
  onSave,
  readOnly = false,
  className = "",
}: WrtEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [mounted, setMounted] = useState(false);

  // Detect current theme from document
  const isDark =
    typeof window !== "undefined" &&
    (document.documentElement.getAttribute("data-theme") === "dark" ||
      (document.documentElement.getAttribute("data-theme") !== "light" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches));

  const theme = isDark ? "wrt-dark" : "wrt-light";

  useEffect(() => {
    setMounted(true);
  }, []);

  function handleEditorDidMount(
    editor: editor.IStandaloneCodeEditor,
    monaco: Monaco,
  ) {
    editorRef.current = editor;

    // Register .wrt language
    registerWrtLanguage(monaco);

    // Add Ctrl+S / Cmd+S save shortcut
    if (onSave) {
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        const value = editor.getValue();
        onSave(value);
      });
    }

    // Focus editor
    editor.focus();
  }

  function handleChange(value: string | undefined) {
    if (onChange && value !== undefined) {
      onChange(value);
    }
  }

  if (!mounted) {
    return (
      <div
        className={`flex items-center justify-center bg-muted ${className}`}
      >
        <div className="text-sm text-muted-foreground">Loading editor...</div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <Editor
        height="100%"
        language="wrt"
        value={content}
        theme={theme}
        onChange={handleChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: "on",
          wordWrap: "on",
          wrappingIndent: "indent",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          insertSpaces: true,
          renderLineHighlight: "all",
          scrollbar: {
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
          },
          // Show whitespace characters for easier editing
          renderWhitespace: "boundary",
        }}
      />
      {onSave && !readOnly && (
        <div className="absolute right-4 top-4 z-10 text-xs text-muted-foreground bg-background/80 px-2 py-1 rounded border border-border">
          {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"}+S to save
        </div>
      )}
    </div>
  );
}
