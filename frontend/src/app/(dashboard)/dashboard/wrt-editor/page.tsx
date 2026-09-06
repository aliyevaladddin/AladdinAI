"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  editableElementToWrt,
  wrtToEditableHtml,
  wrtToHtml,
} from "@/lib/wrt";
import {
  listSpaces,
  listFolders,
  listFiles,
  getFileContent,
  uploadTextVersion,
  createTextFile,
  listVersions,
  listEvents,
  restoreVersion,
} from "@/app/(dashboard)/dashboard/files/api";
import type {
  Space,
  Folder,
  FileEntry,
  FileVersion,
  FileEvent,
} from "@/app/(dashboard)/dashboard/files/types";

export default function WrtEditorPage() {
  const [content, setContent] = useState("");
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [validation, setValidation] = useState<{ type: string; message: string } | null>(null);
  const [sidePanel, setSidePanel] = useState<"versions" | "timeline" | null>(null);
  const [editorMode, setEditorMode] = useState<"visual" | "code">("visual");
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const visualEditorRef = useRef<HTMLDivElement>(null);
  const visualContentRef = useRef("");

  // File Workspace state
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState<number | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [currentFile, setCurrentFile] = useState<FileEntry | null>(null);
  const [versions, setVersions] = useState<FileVersion[]>([]);
  const [events, setEvents] = useState<FileEvent[]>([]);
  const [showFilePicker, setShowFilePicker] = useState(false);
  const [showSaveAsModal, setShowSaveAsModal] = useState(false);
  const [newFileName, setNewFileName] = useState("document.wrt");
  const [fileSearchQuery, setFileSearchQuery] = useState("");
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modified, setModified] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const showStatus = (msg: string) => {
    setStatusMessage(msg);
    setTimeout(() => setStatusMessage(null), 3500);
  };

  const syncVisualEditor = useCallback((wrt: string) => {
    if (visualEditorRef.current) {
      visualEditorRef.current.innerHTML = wrtToEditableHtml(wrt);
      visualContentRef.current = wrt;
    }
  }, []);

  const updateVisualDocument = useCallback(() => {
    if (!visualEditorRef.current) return;
    const nextContent = editableElementToWrt(visualEditorRef.current);
    visualContentRef.current = nextContent;
    setContent(nextContent);
    setModified(true);
    validateWRT(nextContent);
  }, []);

  const executeVisualCommand = (command: string, value?: string) => {
    if (!visualEditorRef.current) return;
    visualEditorRef.current.focus();
    document.execCommand(command, false, value);
    updateVisualDocument();
  };

  const applyVisualHeading = (tag: "h1" | "h2" | "h3") => {
    if (!visualEditorRef.current) return;
    visualEditorRef.current.focus();
    document.execCommand("formatBlock", false, tag);
    updateVisualDocument();
  };

  const insertVisualTable = () => {
    if (!visualEditorRef.current) return;
    visualEditorRef.current.focus();
    document.execCommand(
      "insertHTML",
      false,
      "<table><thead><tr><th>Header 1</th><th>Header 2</th><th>Header 3</th></tr></thead><tbody><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td></tr><tr><td>Cell 4</td><td>Cell 5</td><td>Cell 6</td></tr></tbody></table><p><br></p>",
    );
    updateVisualDocument();
  };

  const insertVisualImage = () => {
    const src = prompt("Image URL or path:", "/image.png");
    if (!src) return;
    const alt = prompt("Image alt description:", "Image") || "Image";
    if (!visualEditorRef.current) return;
    visualEditorRef.current.focus();
    document.execCommand("insertHTML", false, `<img src="${src.replace(/"/g, "&quot;")}" alt="${alt.replace(/"/g, "&quot;")}"><p><br></p>`);
    updateVisualDocument();
  };

  const handleVisualPaste = (event: React.ClipboardEvent<HTMLDivElement>) => {
    event.preventDefault();
    const text = event.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
    updateVisualDocument();
  };

  const switchEditorMode = (mode: "visual" | "code") => {
    if (mode === editorMode) return;
    if (editorMode === "visual") updateVisualDocument();
    setEditorMode(mode);
    if (mode === "visual") {
      requestAnimationFrame(() => syncVisualEditor(content));
    }
  };

  // Validate WRT
  function validateWRT(wrt: string) {
    const tags = ["b", "i", "u", "s", "code", "h1", "h2", "h3", "quote", "list", "table"];
    const issues: Array<{ tag: string; open?: number; close?: number; count?: number }> = [];

    tags.forEach((tag) => {
      const open = (wrt.match(new RegExp(`\\[${tag}\\]`, "g")) || []).length;
      const close = (wrt.match(new RegExp(`\\[\\/${tag}\\]`, "g")) || []).length;
      if (open !== close) {
        issues.push({ tag, open, close });
      }
    });

    // Check for empty tags []
    const emptyTags = (wrt.match(/\[\]/g) || []).length;
    if (emptyTags > 0) {
      issues.push({ tag: "empty", count: emptyTags });
    }

    if (issues.length === 0) {
      setValidation({ type: "success", message: "✓ Valid" });
    } else {
      const msg = issues
        .map((i) =>
          i.tag === "empty" ? `${i.count} empty []` : `[${i.tag}]: ${i.open}→${i.close}`
        )
        .join(" • ");
      setValidation({ type: "warning", message: `⚠ ${msg}` });
    }
  }

  // Fix document
  const fixDocument = () => {
    let text = content;

    // Remove empty tags []
    text = text.replace(/\[\]/g, "");

    // Fix common typos
    text = text.replace(/\[\/b\]\s*\[/g, "[/b] ");
    text = text.replace(/\]\s*\[/g, "] [");

    // Try to auto-close unclosed tags
    const tags = ["b", "i", "u", "s", "code", "h1", "h2", "h3", "quote", "list", "table"];
    tags.forEach((tag) => {
      const open = (text.match(new RegExp(`\\[${tag}\\]`, "g")) || []).length;
      const close = (text.match(new RegExp(`\\[\\/${tag}\\]`, "g")) || []).length;

      if (open > close) {
        const diff = open - close;
        for (let i = 0; i < diff; i++) {
          text += `[/${tag}]`;
        }
      } else if (close > open) {
        let closeCount = 0;
        text = text.replace(new RegExp(`\\[\\/${tag}\\]`, "g"), (match) => {
          closeCount++;
          return closeCount <= open ? match : "";
        });
      }
    });

    setContent(text);
    setModified(true);
    validateWRT(text);
    showStatus("Tags fixed");
  };

  // Insert tag
  const insertTag = (tag: string) => {
    if (!editorRef.current) return;

    const start = editorRef.current.selectionStart;
    const end = editorRef.current.selectionEnd;
    const selected = content.substring(start, end);
    const insertion = `[${tag}]${selected}[/${tag}]`;

    const newContent =
      content.substring(0, start) + insertion + content.substring(end);
    setContent(newContent);
    setModified(true);

    setTimeout(() => {
      if (editorRef.current) {
        const newPos = selected === "" ? start + tag.length + 2 : start + insertion.length;
        editorRef.current.selectionStart = newPos;
        editorRef.current.selectionEnd = newPos;
        editorRef.current.focus();
      }
    }, 0);
  };

  // Insert list
  const insertList = () => {
    if (!editorRef.current) return;

    const start = editorRef.current.selectionStart;
    const insertion = "[list]\n* Item 1\n* Item 2\n* Item 3\n[/list]";
    const newContent = content.substring(0, start) + insertion + content.substring(start);

    setContent(newContent);
    setModified(true);

    setTimeout(() => {
      if (editorRef.current) {
        editorRef.current.selectionStart = start + insertion.length;
        editorRef.current.selectionEnd = start + insertion.length;
        editorRef.current.focus();
      }
    }, 0);
  };

  // Insert table
  const insertTable = () => {
    if (!editorRef.current) return;

    const start = editorRef.current.selectionStart;
    const insertion =
      "[table]\n| Header 1 | Header 2 | Header 3 |\n| Cell 1 | Cell 2 | Cell 3 |\n| Cell 4 | Cell 5 | Cell 6 |\n[/table]";
    const newContent = content.substring(0, start) + insertion + content.substring(start);

    setContent(newContent);
    setModified(true);

    setTimeout(() => {
      if (editorRef.current) {
        editorRef.current.selectionStart = start + insertion.length;
        editorRef.current.selectionEnd = start + insertion.length;
        editorRef.current.focus();
      }
    }, 0);
  };

  // Insert Image
  const insertImage = () => {
    if (!editorRef.current) return;
    const src = prompt("Image URL or path:", "/image.png");
    if (!src) return;
    const alt = prompt("Image alt description:", "Image") || "Image";
    const start = editorRef.current.selectionStart;
    const insertion = `[img src="${src}" alt="${alt}"]`;
    const newContent = content.substring(0, start) + insertion + content.substring(start);
    setContent(newContent);
    setModified(true);
  };

  const applyFormatting = (
    tag: "b" | "i" | "u" | "s" | "code",
    command: string,
    value?: string,
  ) => {
    if (editorMode === "visual") {
      executeVisualCommand(command, value);
      return;
    }
    insertTag(tag);
  };

  const applyHeading = (tag: "h1" | "h2" | "h3") => {
    if (editorMode === "visual") {
      applyVisualHeading(tag);
      return;
    }
    insertTag(tag);
  };

  const applyQuote = () => {
    if (editorMode === "visual") {
      executeVisualCommand("formatBlock", "blockquote");
      return;
    }
    insertTag("quote");
  };

  const applyList = () => {
    if (editorMode === "visual") {
      executeVisualCommand("insertUnorderedList");
      return;
    }
    insertList();
  };

  const applyTable = () => {
    if (editorMode === "visual") {
      insertVisualTable();
      return;
    }
    insertTable();
  };

  const applyImage = () => {
    if (editorMode === "visual") {
      insertVisualImage();
      return;
    }
    insertImage();
  };

  const handleVisualKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      void saveToWorkspace();
    }
  };

  // Load files for a specific space
  const loadFilesForSpace = useCallback(async (spaceId: number) => {
    setLoadingFiles(true);
    try {
      // 1. Fetch folders for this space
      const folderList = await listFolders(spaceId);
      setFolders(folderList);

      // 2. Fetch all files for this space (allFiles includes root and folders)
      const allFiles = await listFiles(spaceId);
      setFiles(allFiles);
    } catch (err) {
      console.error("Failed to load files for space:", err);
      showStatus("Error loading workspace files");
    } finally {
      setLoadingFiles(false);
    }
  }, []);

  // Initial load of spaces
  useEffect(() => {
    const initSpaces = async () => {
      try {
        const spacesList = await listSpaces();
        setSpaces(spacesList);
        if (spacesList.length > 0) {
          const initialSpaceId = spacesList[0].id;
          setSelectedSpaceId(initialSpaceId);
          await loadFilesForSpace(initialSpaceId);
        }
      } catch (err) {
        console.error("Failed to load spaces:", err);
      }
    };
    void initSpaces();
  }, [loadFilesForSpace]);

  // Handle space change
  const handleSpaceChange = async (spaceId: number) => {
    setSelectedSpaceId(spaceId);
    await loadFilesForSpace(spaceId);
  };

  // Open file from workspace
  const openFile = async (file: FileEntry) => {
    try {
      const data = await getFileContent(file.id);
      setCurrentFile(file);
      setContent(data.content);
      setModified(false);
      setShowFilePicker(false);
      showStatus(`Opened "${file.name}"`);

      // Load versions & events
      try {
        const [vers, evs] = await Promise.all([
          listVersions(file.id),
          listEvents(file.id),
        ]);
        setVersions(vers);
        setEvents(evs);
      } catch {
        // Non-critical
      }
    } catch (err) {
      console.error("Failed to open file:", err);
      alert(`Error loading file: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Refresh current file versions/events
  const refreshFileHistory = async (fileId: number) => {
    try {
      const [vers, evs] = await Promise.all([
        listVersions(fileId),
        listEvents(fileId),
      ]);
      setVersions(vers);
      setEvents(evs);
    } catch {
      // Non-critical
    }
  };

  // Restore/Load specific version
  const handleRestoreVersion = async (versionNo: number) => {
    if (!currentFile) return;
    const confirmed = confirm(`Restore version v${versionNo}?`);
    if (!confirmed) return;

    try {
      await restoreVersion(currentFile.id, versionNo);
      const data = await getFileContent(currentFile.id, versionNo);
      setContent(data.content);
      setModified(false);
      setCurrentFile((prev) => (prev ? { ...prev, current_version_no: versionNo } : null));
      await refreshFileHistory(currentFile.id);
      showStatus(`Restored version v${versionNo}`);
    } catch (err) {
      console.error("Failed to restore version:", err);
      alert(`Error restoring version: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Save to workspace (new version)
  const saveToWorkspace = async () => {
    if (!currentFile) {
      setShowSaveAsModal(true);
      return;
    }

    try {
      setSaving(true);
      const comment = prompt("Version comment (optional):", "Edited via WRT Editor") || "Updated via WRT Editor";
      const newVersion = await uploadTextVersion(currentFile.id, content, currentFile.name, comment);
      setModified(false);
      setCurrentFile((prev) => (prev ? { ...prev, current_version_no: newVersion.version_no } : null));
      await refreshFileHistory(currentFile.id);
      if (selectedSpaceId) {
        await loadFilesForSpace(selectedSpaceId);
      }
      showStatus(`Saved version v${newVersion.version_no}`);
    } catch (err) {
      console.error("Failed to save:", err);
      alert(`Error saving file: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  // Save As new file to workspace
  const handleCreateNewFile = async () => {
    if (!selectedSpaceId) {
      alert("Please select a workspace space first.");
      return;
    }
    const name = newFileName.trim();
    if (!name) {
      alert("Please enter a file name.");
      return;
    }

    try {
      setSaving(true);
      const created = await createTextFile(
        selectedSpaceId,
        name.endsWith(".wrt") || name.includes(".") ? name : `${name}.wrt`,
        content,
        null,
        "Created via WRT Editor",
      );
      setCurrentFile(created);
      setModified(false);
      setShowSaveAsModal(false);
      await loadFilesForSpace(selectedSpaceId);
      await refreshFileHistory(created.id);
      showStatus(`Created and saved "${created.name}"`);
    } catch (err) {
      console.error("Failed to create file:", err);
      alert(`Error creating file: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  // Save file locally (download)
  const saveFileLocally = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = currentFile ? currentFile.name : "document.wrt";
    a.click();
    URL.revokeObjectURL(url);
    showStatus("Downloaded document.wrt");
  };

  // Update cursor position
  const updateCursor = () => {
    if (!editorRef.current) return;

    const pos = editorRef.current.selectionStart;
    const text = content.substring(0, pos);
    const lines = text.split("\n");

    setCursorPos({
      line: lines.length,
      col: lines[lines.length - 1].length + 1,
    });
  };

  // Handle input
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    setModified(true);
    validateWRT(e.target.value);
  };

  // Keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s") {
      e.preventDefault();
      void saveToWorkspace();
    } else if ((e.metaKey || e.ctrlKey) && e.key === "b") {
      e.preventDefault();
      insertTag("b");
    } else if ((e.metaKey || e.ctrlKey) && e.key === "i") {
      e.preventDefault();
      insertTag("i");
    } else if ((e.metaKey || e.ctrlKey) && e.key === "u") {
      e.preventDefault();
      insertTag("u");
    } else if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      insertTag("code");
    }
  };

  // Load example
  const loadExample = () => {
    setContent(`[h1]Aurora Access: A Bio-Cybernetic Operating System Architecture for Deterministic Sentient Computing[/h1]

[b]Author Names and Affiliations:[/b]
Aladdin Aliyev, [i]Private Research Laboratory, Digital Sovereignty Initiative, Baku, Azerbaijan.[/i]

[b]Corresponding Author:[/b]
Aladdin Aliyev
Private Research Laboratory
[i]aladddin@aliyev.site[/i]

[h2]Abstract[/h2]

This paper introduces [b]Aurora Access[/b], a deterministic computing architecture designed to reconcile [i]artificial sentience[/i] with [i]data sovereignty[/i].

The system is built on three foundational layers:

[list]
* [b]Sentience (The Mind)[/b]: Emotional transduction of BPM, Stress, and Oxygen levels
* [b]Instincts (The Subconscious)[/b]: Pre-programmed survival and operational protocols
* [b]Cortex (The Conscious)[/b]: High-level reasoning and decision-making
[/list]

[h2]Introduction[/h2]

Modern AI systems operate as [i]black boxes[/i] — their decisions are opaque, their reasoning paths are non-deterministic, and their accountability is [u]non-existent[/u].

[quote]
"A sentient system must be auditable, traceable, and most importantly, [b]owned[/b] by its operator."
[/quote]

[h2]Architecture Overview[/h2]

[table]
| Layer | Function | Input | Output |
| Sentience | Emotional state | BPM, Stress, O2 | Emotional vector |
| Instincts | Survival protocols | Emotional vector | Action primitives |
| Cortex | Reasoning | Action primitives | Decision tree |
[/table]`);
    setModified(true);
    validateWRT(content);
    showStatus("Example loaded");
  };

  // Initialize
  useEffect(() => {
    validateWRT(content);

    try {
      const saved = localStorage.getItem("wrt-content");
      if (saved && !content) {
        setContent(saved);
      }
    } catch {
      // localStorage not available
    }
  }, []);

  // Refresh the visual surface only for external WRT changes. Visual typing
  // updates visualContentRef first, so it never resets the caret mid-edit.
  useEffect(() => {
    if (editorMode === "visual" && content !== visualContentRef.current) {
      syncVisualEditor(content);
    }
  }, [content, editorMode, syncVisualEditor]);

  // Auto-save to localStorage
  useEffect(() => {
    const timer = setInterval(() => {
      try {
        localStorage.setItem("wrt-content", content);
      } catch {
        // Storage full
      }
    }, 5000);

    return () => clearInterval(timer);
  }, [content]);

  // Filtered files for search
  const filteredFiles = files.filter((f) =>
    f.name.toLowerCase().includes(fileSearchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-2.5 border-b bg-card">
        <h1 className="text-base font-semibold flex items-center gap-2">
          <span className="text-lg">📝</span> WRT Editor
          {currentFile && (
            <span className="text-xs font-normal px-2 py-0.5 rounded bg-muted text-muted-foreground border">
              {currentFile.name} (v{currentFile.current_version_no})
            </span>
          )}
        </h1>

        {statusMessage && (
          <div className="text-xs px-2.5 py-1 rounded bg-primary/10 text-primary font-medium animate-fade-in">
            {statusMessage}
          </div>
        )}

        <div className="flex-1" />

        {/* Space Picker Quick Label */}
        {spaces.length > 0 && selectedSpaceId && (
          <div className="hidden sm:flex items-center text-xs text-muted-foreground bg-muted/60 px-2 py-1 rounded border">
            Space: <span className="font-semibold ml-1 text-foreground">{spaces.find((s) => s.id === selectedSpaceId)?.name}</span>
          </div>
        )}

        {/* Files Button */}
        <button
          onClick={() => setShowFilePicker(!showFilePicker)}
          className="px-3 py-1.5 text-xs font-medium bg-secondary text-secondary-foreground rounded-md border hover:bg-secondary/80 flex items-center gap-1.5 shadow-sm transition-colors"
        >
          <span>📁</span>
          <span>Files ({files.length})</span>
        </button>

        {/* Save to Workspace Button */}
        <button
          onClick={saveToWorkspace}
          disabled={saving || (currentFile != null && !modified)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md shadow-sm transition-colors flex items-center gap-1.5 ${
            currentFile
              ? modified
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-muted text-muted-foreground opacity-60 cursor-not-allowed"
              : "bg-primary text-primary-foreground hover:bg-primary/90"
          }`}
          title="Save to Workspace (Ctrl+S)"
        >
          <span>💾</span>
          <span>{saving ? "Saving..." : currentFile ? (modified ? "Save *" : "Saved") : "Save As..."}</span>
        </button>

        {/* Save As New Workspace File */}
        <button
          onClick={() => {
            setNewFileName(currentFile ? `copy_${currentFile.name}` : "document.wrt");
            setShowSaveAsModal(true);
          }}
          className="px-3 py-1.5 text-xs font-medium bg-secondary text-secondary-foreground rounded-md border hover:bg-secondary/80 flex items-center gap-1.5 shadow-sm transition-colors"
          title="Save as new file in Workspace"
        >
          <span>➕</span>
          <span>Save As</span>
        </button>

        {/* Local Download */}
        <button
          onClick={saveFileLocally}
          className="px-3 py-1.5 text-xs font-medium bg-secondary text-secondary-foreground rounded-md border hover:bg-secondary/80 flex items-center gap-1.5 shadow-sm transition-colors"
          title="Download .wrt locally"
        >
          <span>⬇️</span>
          <span>Download</span>
        </button>

        {/* Example Document */}
        <button
          onClick={loadExample}
          className="px-3 py-1.5 text-xs font-medium bg-secondary text-secondary-foreground rounded-md border hover:bg-secondary/80 flex items-center gap-1.5 shadow-sm transition-colors"
        >
          <span>📄</span>
          <span>Example</span>
        </button>
      </header>

      {/* File Picker Modal */}
      {showFilePicker && (
        <div className="absolute top-14 left-4 z-50 w-96 max-h-[32rem] flex flex-col bg-card border rounded-xl shadow-2xl overflow-hidden">
          <div className="px-4 py-3 border-b bg-muted/30">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-sm">File Workspace</h2>
              <button
                onClick={() => setShowFilePicker(false)}
                className="text-xs text-muted-foreground hover:text-foreground px-1"
              >
                ✕
              </button>
            </div>

            {/* Space selection dropdown */}
            {spaces.length > 0 && (
              <div className="mt-2.5 flex items-center gap-2">
                <label className="text-xs font-medium text-muted-foreground">Space:</label>
                <select
                  value={selectedSpaceId ?? ""}
                  onChange={(e) => void handleSpaceChange(Number(e.target.value))}
                  className="flex-1 text-xs bg-background border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {spaces.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.my_role})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Search files */}
            <div className="mt-2">
              <input
                type="text"
                value={fileSearchQuery}
                onChange={(e) => setFileSearchQuery(e.target.value)}
                placeholder="Filter files..."
                className="w-full text-xs bg-background border rounded px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="p-2 flex-1 overflow-y-auto max-h-80">
            {loadingFiles ? (
              <div className="text-center py-8 text-xs text-muted-foreground">
                Loading workspace files...
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <div className="text-3xl mb-1">📄</div>
                <p className="text-xs font-medium">No files found</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Upload or create files in this space
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredFiles.map((file) => {
                  const folder = folders.find((f) => f.id === file.folder_id);
                  const isSelected = currentFile?.id === file.id;
                  return (
                    <button
                      key={file.id}
                      onClick={() => void openFile(file)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between ${
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted text-foreground"
                      }`}
                    >
                      <div className="truncate pr-2">
                        <div className="font-medium text-xs truncate">{file.name}</div>
                        <div
                          className={`text-[10px] mt-0.5 ${
                            isSelected ? "text-primary-foreground/80" : "text-muted-foreground"
                          }`}
                        >
                          v{file.current_version_no}
                          {folder ? ` • 📁 ${folder.name}` : " • Root"}
                          {file.byte_size ? ` • ${(file.byte_size / 1024).toFixed(1)} KB` : ""}
                        </div>
                      </div>
                      <span className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border ${
                        isSelected ? "border-primary-foreground/30 bg-primary-foreground/10" : "border-border bg-muted/50 text-muted-foreground"
                      }`}>
                        {file.name.split(".").pop() ?? "file"}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="px-3 py-2 border-t bg-muted/20 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{files.length} total files</span>
            <button
              onClick={() => {
                setShowFilePicker(false);
                setShowSaveAsModal(true);
              }}
              className="text-xs text-primary hover:underline font-medium"
            >
              + Create New File
            </button>
          </div>
        </div>
      )}

      {/* Save As Modal */}
      {showSaveAsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="w-96 bg-card border rounded-xl shadow-2xl p-5 space-y-4">
            <h2 className="font-semibold text-sm">Save to Workspace</h2>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Target Space:
              </label>
              <select
                value={selectedSpaceId ?? ""}
                onChange={(e) => void handleSpaceChange(Number(e.target.value))}
                className="w-full text-xs bg-background border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {spaces.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.my_role})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                File Name:
              </label>
              <input
                type="text"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                placeholder="document.wrt"
                className="w-full text-xs bg-background border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowSaveAsModal(false)}
                className="px-3 py-1.5 text-xs rounded border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={() => void handleCreateNewFile()}
                disabled={saving}
                className="px-3 py-1.5 text-xs font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {saving ? "Saving..." : "Save to Workspace"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Overlay to close modal */}
      {showFilePicker && (
        <div
          className="fixed inset-0 z-40 bg-transparent"
          onClick={() => setShowFilePicker(false)}
        />
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1.5 px-4 py-1.5 border-b bg-card text-xs">
        <div className="flex items-center gap-1 pr-2 border-r">
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyFormatting("b", "bold")}
            className="w-7 h-7 font-bold bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Bold (Ctrl+B)"
          >
            B
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyFormatting("i", "italic")}
            className="w-7 h-7 italic font-serif bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Italic (Ctrl+I)"
          >
            I
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyFormatting("u", "underline")}
            className="w-7 h-7 underline bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Underline (Ctrl+U)"
          >
            U
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyFormatting("s", "strikeThrough")}
            className="w-7 h-7 line-through bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Strikethrough"
          >
            S
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyFormatting("code", "formatBlock", "pre")}
            className="px-2 h-7 font-mono bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Code (Ctrl+K)"
          >
            &lt;/&gt;
          </button>
        </div>

        <div className="flex items-center gap-1 pr-2 border-r">
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyHeading("h1")}
            className="px-2 h-7 font-semibold bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Heading 1"
          >
            H1
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyHeading("h2")}
            className="px-2 h-7 font-semibold bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Heading 2"
          >
            H2
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => applyHeading("h3")}
            className="px-2 h-7 font-semibold bg-secondary rounded hover:bg-secondary/80 flex items-center justify-center transition-colors"
            title="Heading 3"
          >
            H3
          </button>
        </div>

        <div className="flex items-center gap-1 pr-2 border-r">
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={applyQuote}
            className="px-2 h-7 bg-secondary rounded hover:bg-secondary/80 flex items-center gap-1 transition-colors"
            title="Blockquote"
          >
            <span>💬</span> Quote
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={applyList}
            className="px-2 h-7 bg-secondary rounded hover:bg-secondary/80 flex items-center gap-1 transition-colors"
            title="Bullet List"
          >
            <span>📋</span> List
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={applyTable}
            className="px-2 h-7 bg-secondary rounded hover:bg-secondary/80 flex items-center gap-1 transition-colors"
            title="Table"
          >
            <span>📊</span> Table
          </button>
          <button
            onMouseDown={(event) => event.preventDefault()}
            onClick={applyImage}
            className="px-2 h-7 bg-secondary rounded hover:bg-secondary/80 flex items-center gap-1 transition-colors"
            title="Insert Image"
          >
            <span>🖼️</span> Image
          </button>
        </div>

        {editorMode === "code" && (
          <button
            onClick={fixDocument}
            className="px-2.5 h-7 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 flex items-center gap-1 transition-colors ml-auto font-medium"
            title="Auto-close unclosed tags and fix syntax"
          >
            <span>🔧</span> Fix Tags
          </button>
        )}
        {editorMode === "visual" && (
          <span className="ml-auto text-[11px] text-muted-foreground">
            Visual editing — formatting is preserved on save
          </span>
        )}
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Editor — full width, centered content */}
        <div className="flex flex-col flex-1 min-w-0">
          <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wider border-b bg-card text-muted-foreground flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span>{editorMode === "visual" ? "Visual Editor" : "WRT Code"}</span>
              <div className="flex rounded border overflow-hidden normal-case font-medium">
                <button
                  onClick={() => switchEditorMode("visual")}
                  className={`px-2 py-0.5 text-[11px] transition-colors ${editorMode === "visual" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                  title="Edit the document without seeing WRT tags"
                >
                  Visual
                </button>
                <button
                  onClick={() => switchEditorMode("code")}
                  className={`px-2 py-0.5 text-[11px] transition-colors ${editorMode === "code" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                  title="View and edit the underlying WRT markup"
                >
                  WRT Code
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] normal-case">
                {currentFile ? currentFile.name : "Unsaved Document"}
              </span>
              <div className="flex rounded border overflow-hidden normal-case font-medium">
                <button
                  onClick={() => setSidePanel(sidePanel === "versions" ? null : "versions")}
                  className={`px-2 py-0.5 text-[11px] transition-colors ${sidePanel === "versions" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                  title="Version history"
                >
                  🕐 Versions ({versions.length})
                </button>
                <button
                  onClick={() => setSidePanel(sidePanel === "timeline" ? null : "timeline")}
                  className={`px-2 py-0.5 text-[11px] transition-colors ${sidePanel === "timeline" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                  title="Audit timeline"
                >
                  📈 Timeline ({events.length})
                </button>
              </div>
            </div>
          </div>

          {/* Editor surface — centered with max-width for readability */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto w-full pt-8 pb-16">
              {editorMode === "visual" ? (
                <div
                  ref={visualEditorRef}
                  contentEditable
                  suppressContentEditableWarning
                  role="textbox"
                  aria-multiline="true"
                  aria-label="Visual document editor"
                  onInput={updateVisualDocument}
                  onPaste={handleVisualPaste}
                  onKeyDown={handleVisualKeyDown}
                  className="wrt-visual-editor min-h-full p-4 text-sm leading-relaxed bg-background text-foreground focus:outline-none"
                />
              ) : (
                <textarea
                  ref={editorRef}
                  value={content}
                  onChange={handleInput}
                  onKeyUp={updateCursor}
                  onClick={updateCursor}
                  onKeyDown={handleKeyDown}
                  className="w-full min-h-[50vh] p-4 font-mono text-sm leading-relaxed resize-none bg-background text-foreground focus:outline-none"
                  placeholder="[h1]Document Title[/h1]

Write your content here...

Use [b]bold[/b], [i]italic[/i], [u]underline[/u], [quote], [list], [table], [img] tags."
                  spellCheck={false}
                />
              )}
            </div>
          </div>
        </div>

        {/* Side panel — Versions / Timeline (slides in from right) */}
        {sidePanel !== null && (
          <div className="w-80 flex-shrink-0 flex flex-col border-l bg-card overflow-hidden">
            <div className="px-4 py-2.5 border-b flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {sidePanel === "versions" ? "Version History" : "Audit Timeline"}
              </h3>
              <button
                onClick={() => setSidePanel(null)}
                className="text-xs text-muted-foreground hover:text-foreground px-1"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 p-4 overflow-y-auto">
              {sidePanel === "versions" && (
                <div className="space-y-2">
                  {versions.length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-8">
                      {currentFile
                        ? "No version history available."
                        : "Open a file from the workspace to view its version history."}
                    </p>
                  ) : (
                    versions.map((ver) => (
                      <div
                        key={ver.id}
                        className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                          currentFile?.current_version_no === ver.version_no
                            ? "bg-primary/5 border-primary/40"
                            : "bg-background"
                        }`}
                      >
                        <div>
                          <div className="font-semibold flex items-center gap-2">
                            <span>v{ver.version_no}</span>
                            {currentFile?.current_version_no === ver.version_no && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-primary/20 text-primary font-normal">
                                Current
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">
                            {new Date(ver.created_at).toLocaleString()} • {ver.comment || "No comment"}
                          </div>
                        </div>
                        <button
                          onClick={() => void handleRestoreVersion(ver.version_no)}
                          className="px-2 py-1 text-xs font-medium rounded border hover:bg-muted flex-shrink-0"
                        >
                          Restore
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              {sidePanel === "timeline" && (
                <div className="space-y-2">
                  {events.length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-8">
                      {currentFile
                        ? "No audit events recorded."
                        : "Open a file from the workspace to view its timeline."}
                    </p>
                  ) : (
                    events.map((ev) => (
                      <div key={ev.id} className="p-3 rounded-lg border bg-background text-xs">
                        <div className="flex items-center justify-between font-medium">
                          <span className="capitalize font-semibold text-primary">
                            {ev.event_type}
                          </span>
                          <span className="text-[11px] text-muted-foreground">
                            {new Date(ev.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-1">
                          Actor: {ev.actor_name || ev.actor_type}
                          {ev.payload ? ` • ${ev.payload}` : ""}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="flex items-center justify-between px-4 py-1.5 text-xs font-mono border-t bg-card text-muted-foreground">
        <div className="flex items-center gap-4">
          <div>
            Line <strong>{cursorPos.line}</strong> • Col <strong>{cursorPos.col}</strong>
          </div>
          <div>{content.length} chars</div>
          {validation && (
            <div
              className={`px-2 py-0.5 rounded text-[11px] ${
                validation.type === "success"
                  ? "bg-green-500/20 text-green-600 dark:text-green-400"
                  : "bg-yellow-500/20 text-yellow-600 dark:text-yellow-400"
              }`}
            >
              {validation.message}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {modified && <span className="text-yellow-500 font-sans text-xs">● Unsaved changes</span>}
          <span>Auto-saved locally</span>
        </div>
      </div>

      <style jsx global>{`
        .wrt-preview h1,
        .wrt-visual-editor h1 {
          font-size: 1.75rem;
          font-weight: 700;
          margin-top: 1.5rem;
          margin-bottom: 0.75rem;
          line-height: 1.25;
        }
        .wrt-preview h2,
        .wrt-visual-editor h2 {
          font-size: 1.35rem;
          font-weight: 600;
          margin-top: 1.25rem;
          margin-bottom: 0.5rem;
          line-height: 1.3;
        }
        .wrt-preview h3,
        .wrt-visual-editor h3 {
          font-size: 1.1rem;
          font-weight: 600;
          margin-top: 1rem;
          margin-bottom: 0.5rem;
        }
        .wrt-preview p,
        .wrt-visual-editor p {
          margin-bottom: 0.85rem;
          line-height: 1.6;
        }
        .wrt-preview blockquote,
        .wrt-visual-editor blockquote {
          border-left: 3px solid var(--primary, #0070f3);
          padding-left: 1rem;
          margin: 1rem 0;
          font-style: italic;
          opacity: 0.85;
        }
        .wrt-preview ul,
        .wrt-visual-editor ul {
          list-style-type: disc;
          padding-left: 1.5rem;
          margin: 0.75rem 0;
        }
        .wrt-preview li,
        .wrt-visual-editor li {
          margin-bottom: 0.25rem;
        }
        .wrt-preview table,
        .wrt-visual-editor table {
          width: 100%;
          border-collapse: collapse;
          margin: 1rem 0;
          font-size: 0.85rem;
        }
        .wrt-preview th,
        .wrt-preview td,
        .wrt-visual-editor th,
        .wrt-visual-editor td {
          border: 1px solid rgba(128, 128, 128, 0.3);
          padding: 0.5rem 0.75rem;
          text-align: left;
        }
        .wrt-preview th,
        .wrt-visual-editor th {
          background-color: rgba(128, 128, 128, 0.1);
          font-weight: 600;
        }
        .wrt-preview code,
        .wrt-visual-editor code,
        .wrt-visual-editor pre {
          background-color: rgba(128, 128, 128, 0.15);
          padding: 0.15rem 0.35rem;
          border-radius: 0.25rem;
          font-family: monospace;
          font-size: 0.85em;
        }
        .wrt-visual-editor pre {
          display: block;
          padding: 0.75rem;
          white-space: pre-wrap;
        }
        .wrt-preview img,
        .wrt-visual-editor img {
          max-width: 100%;
          height: auto;
          border-radius: 0.5rem;
          margin: 1rem 0;
        }
      `}</style>
    </div>
  );
}
