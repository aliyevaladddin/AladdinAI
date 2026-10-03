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

/** One validation problem, shaped like the native engine's issue objects. */
export interface WrtIssue {
  line: number;
  col?: number;
  tag: string;
  message: string;
  /** 0 is an error in the engine's own encoding. */
  severity: number;
}

interface WrtEditorProps {
  content: string;
  onChange?: (value: string) => void;
  onSave?: (value: string) => void;
  /** Wrap the current selection in a tag; used by the toolbar and Ctrl+key bindings. */
  onFormat?: (tag: string) => void;
  onCursorChange?: (pos: { line: number; col: number }) => void;
  /** Validation problems to underline. Recomputed by the caller, not here. */
  issues?: WrtIssue[];
  /**
   * Receives the live Monaco editor once mounted, so the page's own toolbar
   * buttons can act on the real selection instead of a second, parallel notion
   * of "where the cursor is".
   */
  editorRef?: React.MutableRefObject<editor.IStandaloneCodeEditor | null>;
  readOnly?: boolean;
  className?: string;
}

/**
 * The WRT tag vocabulary, mirroring VALID_TAGS in backend/native/wrt/wrt_engine.c.
 *
 * This is a hand-maintained copy, and a diverging one is exactly how the old
 * tokenizer ended up highlighting 11 tags while the engine knew 17 — `tr/th/td`
 * (the whole table vocabulary) and `link/url` rendered as plain text. Anything
 * added to VALID_TAGS needs a line here.
 */
const WRT_TAGS = [
  { name: "b", desc: "Bold text", kind: "inline" },
  { name: "i", desc: "Italic text", kind: "inline" },
  { name: "u", desc: "Underlined text", kind: "inline" },
  { name: "s", desc: "Struck-through text", kind: "inline" },
  { name: "code", desc: "Inline monospace code", kind: "inline" },
  { name: "h1", desc: "Heading, level 1", kind: "heading" },
  { name: "h2", desc: "Heading, level 2", kind: "heading" },
  { name: "h3", desc: "Heading, level 3", kind: "heading" },
  { name: "quote", desc: "Block quotation", kind: "block" },
  { name: "list", desc: "Bulleted list (items as * text)", kind: "block" },
  { name: "table", desc: "Table (rows as | a | b |)", kind: "block" },
  { name: "tr", desc: "Table row", kind: "table" },
  { name: "th", desc: "Table header cell", kind: "table" },
  { name: "td", desc: "Table data cell", kind: "table" },
  { name: "img", desc: 'Image — [img src="..." alt="..."]', kind: "void" },
  { name: "link", desc: "Hyperlink — [link url=...]text[/link]", kind: "inline" },
  { name: "url", desc: "Bare URL", kind: "void" },
] as const;

const INLINE_TAGS = WRT_TAGS.filter((t) => t.kind === "inline" || t.kind === "heading");
const VOID_TAGS = WRT_TAGS.filter((t) => t.kind === "void");
/**
 * Themes the app renders with a light surface. Must stay in sync with the
 * `color-scheme: light` block in app/globals.css — mist-sapphire is family
 * "dim" but is still a light surface, so this is an explicit list, not a
 * family lookup.
 */
const LIGHT_THEMES: ReadonlySet<string> = new Set([
  "ivory-indigo",
  "linen-sand",
  "mist-sapphire",
]);

/**
 * Whether the app is currently on a light theme, read from the data-theme
 * attribute ThemeProvider puts on <html>. The app has no "dark" theme id, so
 * keying off that attribute (as this used to) never matched and the check
 * degraded to the OS prefers-color-scheme media query — which is unrelated to
 * the in-app theme, leaving a white Monaco on a dark page (or the reverse).
 */
function isAppDarkTheme(): boolean {
  if (typeof document === "undefined") return true;
  const current = document.documentElement.getAttribute("data-theme");
  // No attribute yet means the pre-paint init script hasn't run; the default
  // theme (violet-amber) is dark.
  if (!current) return true;
  return !LIGHT_THEMES.has(current);
}

/** Tags the toolbar could wrap a selection in. */
const WRAPPABLE_TAGS = WRT_TAGS.filter((t) => t.kind === "inline" || t.kind === "block");

/**
 * Register .wrt language with Monaco for syntax highlighting
 */
function registerWrtLanguage(monaco: Monaco) {
  // Only register once
  if (monaco.languages.getLanguages().some((lang: { id: string }) => lang.id === "wrt")) {
    return;
  }

  monaco.languages.register({ id: "wrt" });

  const inlineNames = INLINE_TAGS.map((t) => t.name).join("|");
  const blockNames = WRT_TAGS.filter((t) => t.kind === "block" || t.kind === "table")
    .map((t) => t.name)
    .join("|");

  monaco.languages.setMonarchTokensProvider("wrt", {
    tokenizer: {
      root: [
        // Heading tags
        [/\[h[123]\]/, "tag.heading.open"],
        [/\[\/h[123]\]/, "tag.heading.close"],

        // Inline formatting tags
        [new RegExp(`\\[(${inlineNames})\\]`), "tag.inline.open"],
        [new RegExp(`\\[\\/(${inlineNames})\\]`), "tag.inline.close"],

        // Block tags, including the table vocabulary (tr/th/td)
        [new RegExp(`\\[(${blockNames})\\]`), "tag.block.open"],
        [new RegExp(`\\[\\/(${blockNames})\\]`), "tag.block.close"],

        // Self-closing tags with attributes. The attribute values are matched
        // lazily so a `]` inside a quoted value cannot truncate the tag — the
        // same class of bug find_self_closing_tag_end() guards against in C.
        [/\[img\s+src="[^"]*"(?:\s+alt="[^"]*")?\]/, "tag.image"],
        [/\[link\s+url="[^"]*"\](?=\S)/, "tag.link"],
        [/\[url[^\]]*\]/, "tag.link"],
        [/\[(?:img|link|url)\b[^\]]*\]/, "tag.image"],

        // Attribute strings inside any bracketed tag
        [/"[^"]*"/, "tag.attribute"],
        [/\b(src|alt|url)="/, "tag.attribute.name"],

        // List items
        [/^\*\s+/, "list.item"],

        // Table rows
        [/^\|.*\|$/, "table.row"],
      ],
    },
  });

  // Autocomplete over the tag vocabulary. Triggering on "[" is the whole point:
  // the user opens a bracket to get a tag, and the list is right there.
  monaco.languages.registerCompletionItemProvider("wrt", {
    triggerCharacters: ["["],
    provideCompletionItems(
      model: editor.ITextModel,
      position: { lineNumber: number; column: number }
    ) {
      const word = model.getWordUntilPosition(position);
      const lineToCursor = model
        .getValueInRange({
          startLineNumber: position.lineNumber,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        })
        .toLowerCase();

      // Only offer inside a bracket, never mid-prose.
      if (!lineToCursor.includes("[")) {
        return { suggestions: [] };
      }

      const afterBracket = lineToCursor.slice(lineToCursor.lastIndexOf("[") + 1);
      // Closing tags would only be noise while the user is opening one.
      if (afterBracket.startsWith("/")) {
        return { suggestions: [] };
      }

      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      return {
        suggestions: [
          ...WRT_TAGS.map((tag) => ({
            label: `[${tag.name}]`,
            kind: monaco.languages.CompletionItemKind.Field,
            insertText:
              tag.kind === "void" ? `[${tag.name}]` : `[${tag.name}]|[/${tag.name}]`,
            // Keeps the caret between the tags; Monaco moves it to the "|".
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            detail: tag.desc,
            documentation: `[${tag.name}] … [/${tag.name}]`,
            range,
          })),
          ...VOID_TAGS.map((tag) => ({
            label: `/${tag.name}`,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: `/${tag.name}]`,
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            detail: `Close [${tag.name}]`,
            range,
          })),
        ],
      };
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
      { token: "tag.link", foreground: "0000CC" },
      { token: "tag.attribute.name", foreground: "A31515" },
      { token: "tag.attribute", foreground: "A31515" },
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
      { token: "tag.link", foreground: "9CDCFE" },
      { token: "tag.attribute.name", foreground: "9CDCFE" },
      { token: "tag.attribute", foreground: "CE9178" },
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
  onFormat,
  onCursorChange,
  issues,
  editorRef: externalEditorRef,
  readOnly = false,
  className = "",
}: WrtEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isDark, setIsDark] = useState(isAppDarkTheme);

  const theme = isDark ? "wrt-dark" : "wrt-light";

  useEffect(() => {
    setMounted(true);
  }, []);

  // Follow live theme switches: ThemeProvider writes data-theme on <html>,
  // which is exactly what we observe. Without this the Monaco theme froze at
  // whatever the page was on when the editor first mounted.
  useEffect(() => {
    const observer = new MutationObserver(() => setIsDark(isAppDarkTheme()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    // Catch a switch that happened between first render and subscribing.
    setIsDark(isAppDarkTheme());
    return () => observer.disconnect();
  }, []);

  // The editor is mounted after first paint, so a validation report that lands
  // before then would find no model to decorate. Re-apply whenever it changes.
  useEffect(() => {
    const ed = editorRef.current;
    if (!ed) return;
    const monaco = (ed as unknown as { _wrtMonaco?: Monaco })._wrtMonaco;
    const model = ed.getModel();
    if (!monaco || !model || !issues) return;

    monaco.editor.setModelMarkers(
      model,
      "wrt",
      issues.map((issue) => {
        const line = Math.min(Math.max(issue.line, 1), model.getLineCount());
        const lineLength = model.getLineMaxColumn(line);
        const col = Math.min(Math.max(issue.col ?? 1, 1), lineLength);
        return {
          startLineNumber: line,
          endLineNumber: line,
          startColumn: col,
          // A zero-width marker is invisible in the gutter; run it to the end
          // of the line so the offending tag is actually underlined.
          endColumn: Math.min(col + Math.max(issue.tag.length + 2, 1), lineLength),
          message: issue.message,
          severity:
            issue.severity === 0
              ? monaco.MarkerSeverity.Error
              : monaco.MarkerSeverity.Warning,
          source: "wrt",
        };
      })
    );
  }, [issues, mounted]);

  function handleEditorDidMount(
    editor: editor.IStandaloneCodeEditor,
    monaco: Monaco,
  ) {
    editorRef.current = editor;
    if (externalEditorRef) externalEditorRef.current = editor;
    // Kept on the instance so the markers effect can reach the API without
    // widening the public props to carry a whole Monaco reference.
    (editor as unknown as { _wrtMonaco?: Monaco })._wrtMonaco = monaco;

    // Ctrl+S / Cmd+S save
    if (onSave) {
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        onSave(editor.getValue());
      });
    }

    // Tag shortcuts, carried over from the retired C Editor (wrt_editor.c bound
    // the same four) and routed through onFormat so the page keeps one
    // implementation of "wrap the selection in a tag".
    if (onFormat) {
      const BINDINGS: Array<[number, string]> = [
        [monaco.KeyCode.KeyB, "b"],
        [monaco.KeyCode.KeyI, "i"],
        [monaco.KeyCode.KeyU, "u"],
        [monaco.KeyCode.KeyK, "code"],
      ];
      for (const [keyCode, tag] of BINDINGS) {
        editor.addCommand(monaco.KeyMod.CtrlCmd | keyCode, () => onFormat(tag));
      }
    }

    // NOTE: tag auto-close on "]" used to live here, ported from
    // wrt_auto_close_tag() in wrt_editor.c. It scanned backwards with
    // lastIndexOf("[") and took the tag name as everything from "[" to end of
    // line, which both diverged from the C bounds and had no guard for column 0
    // — on "] " it inserted stray characters (a literal "$") instead of [/tag].
    // It is removed on purpose: the "[" completion provider above already inserts
    // [tag]|[/tag] with the caret between them, covering the same case without
    // hand-rolled string arithmetic. See project_aladdinai_wrt_editor_dataloss_oct02.

    if (onCursorChange) {
      const report = () => {
        const pos = editor.getPosition();
        if (pos) onCursorChange({ line: pos.lineNumber, col: pos.column });
      };
      editor.onDidChangeCursorPosition(report);
    }

    editor.focus();
  }

  function handleChange(value: string | undefined) {
    if (onChange && value !== undefined) {
      onChange(value);
    }
  }

  if (!mounted) {
    return (
      <div className={`flex items-center justify-center bg-muted ${className}`}>
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
        // Language + wrt-dark/wrt-light themes must exist BEFORE the wrapper
        // applies the `theme` prop. Registered in onMount they came too late:
        // Monaco silently fell back to its default light theme on a dark page.
        beforeMount={registerWrtLanguage}
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
          // Typo tolerance and a find widget: the two things a bare textarea
          // could never offer, and the reason this mode is worth having.
          quickSuggestions: { other: true, comments: false, strings: false },
          suggestOnTriggerCharacters: true,
          acceptSuggestionOnEnter: "on",
          tabCompletion: "on",
          wordBasedSuggestions: "off",
          bracketPairColorization: { enabled: true },
          guides: { bracketPairs: false, indentation: true },
          scrollbar: {
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
          },
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
