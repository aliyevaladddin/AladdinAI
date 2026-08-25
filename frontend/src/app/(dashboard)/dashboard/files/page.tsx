// NOTICE: This file is protected under RCF-PL
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Clock,
  Download,
  File as FileIcon,
  Folder as FolderIcon,
  FolderOpen,
  FolderPlus,
  History,
  Home,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SegmentedTabs, type TabDef } from "@/components/ui/segmented-tabs";
import * as api from "./api";
import type { FileEntry, FileEvent, FileVersion, Folder, Space } from "./types";

type PanelTab = "versions" | "timeline";

const PANEL_TABS: TabDef<PanelTab>[] = [
  { id: "versions", label: "Versions", icon: History },
  { id: "timeline", label: "Timeline", icon: Clock },
];

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function FilesPage() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [spaceId, setSpaceId] = useState<number | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [folderId, setFolderId] = useState<number | null>(null);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [selectedFile, setSelectedFile] = useState<FileEntry | null>(null);
  const [panelTab, setPanelTab] = useState<PanelTab>("versions");
  const [versions, setVersions] = useState<FileVersion[]>([]);
  const [events, setEvents] = useState<FileEvent[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeSpace = spaces.find((s) => s.id === spaceId) ?? null;
  const canEdit = activeSpace?.my_role === "owner" || activeSpace?.my_role === "editor";

  /* ── data loading ─────────────────────────────────────────────── */

  useEffect(() => {
    let cancelled = false;
    api
      .listSpaces()
      .then((list) => {
        if (cancelled) return;
        setSpaces(list);
        setSpaceId((prev) => prev ?? list[0]?.id ?? null);
      })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load spaces"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const reloadFiles = useCallback(async () => {
    if (spaceId == null) return;
    try {
      const [folderList, fileList] = await Promise.all([
        api.listFolders(spaceId),
        api.listFiles(spaceId, folderId),
      ]);
      setFolders(folderList);
      setFiles(fileList);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load files");
    }
  }, [spaceId, folderId]);

  useEffect(() => {
    void reloadFiles();
  }, [reloadFiles]);

  useEffect(() => {
    if (!selectedFile) return;
    let cancelled = false;
    api
      .listVersions(selectedFile.id)
      .then((v) => !cancelled && setVersions(v))
      .catch((e: unknown) =>
        toast.error(e instanceof Error ? e.message : "Failed to load versions"),
      );
    api
      .listEvents(selectedFile.id)
      .then((ev) => !cancelled && setEvents(ev))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [selectedFile]);

  /* ── actions ──────────────────────────────────────────────────── */

  const refreshSelected = useCallback(
    async (fileId: number) => {
      const updated = await api.listFiles(spaceId ?? 0, folderId);
      setFiles(updated);
      const fresh = updated.find((f) => f.id === fileId) ?? null;
      setSelectedFile(fresh);
      setVersions(await api.listVersions(fileId));
      setEvents(await api.listEvents(fileId));
    },
    [spaceId, folderId],
  );

  const handleUpload = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0 || spaceId == null) return;
      setBusy(true);
      try {
        for (const file of Array.from(fileList)) {
          await api.uploadFile(spaceId, file, folderId);
          toast.success(`Uploaded ${file.name}`);
        }
        await reloadFiles();
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setBusy(false);
      }
    },
    [spaceId, folderId, reloadFiles],
  );

  const handleNewFolder = useCallback(async () => {
    if (spaceId == null) return;
    const name = window.prompt("Folder name");
    if (!name?.trim()) return;
    try {
      await api.createFolder(spaceId, name.trim(), folderId);
      await reloadFiles();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create folder");
    }
  }, [spaceId, folderId, reloadFiles]);

  const handleRenameFolder = useCallback(
    async (folder: Folder) => {
      const name = window.prompt("New folder name", folder.name);
      if (!name?.trim() || name.trim() === folder.name) return;
      try {
        await api.renameFolder(folder.id, name.trim());
        await reloadFiles();
        toast.success("Folder renamed");
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Rename failed");
      }
    },
    [reloadFiles],
  );

  const handleDeleteFolder = useCallback(
    async (folder: Folder) => {
      if (
        !window.confirm(
          `Delete folder "${folder.name}"? Files inside move back to the space root.`,
        )
      )
        return;
      try {
        await api.deleteFolder(folder.id);
        if (folderId === folder.id) setFolderId(null);
        await reloadFiles();
        toast.success("Folder deleted");
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Delete failed");
      }
    },
    [folderId, reloadFiles],
  );

  const handleCreateSpace = useCallback(async () => {
    const name = window.prompt("Space name");
    if (!name?.trim()) return;
    try {
      const space = await api.createSpace(name.trim());
      setSpaces((prev) => [...prev, space]);
      setSpaceId(space.id);
      setFolderId(null);
      setSelectedFile(null);
      toast.success(`Space "${space.name}" created`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create space");
    }
  }, []);

  const handleMove = useCallback(
    async (targetFolderId: number | null) => {
      if (!selectedFile) return;
      try {
        await api.moveFile(selectedFile.id, targetFolderId);
        toast.success("Moved");
        await refreshSelected(selectedFile.id);
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Move failed");
      }
    },
    [selectedFile, refreshSelected],
  );

  const handleRename = useCallback(async () => {
    if (!selectedFile) return;
    const name = window.prompt("New name", selectedFile.name);
    if (!name?.trim() || name.trim() === selectedFile.name) return;
    try {
      await api.renameFile(selectedFile.id, name.trim());
      toast.success("Renamed");
      await refreshSelected(selectedFile.id);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Rename failed");
    }
  }, [selectedFile, refreshSelected]);

  const handleDelete = useCallback(
    async (file: FileEntry) => {
      if (!window.confirm(`Delete "${file.name}"? History stays recoverable.`)) return;
      try {
        await api.deleteFile(file.id);
        toast.success("Deleted");
        setSelectedFile(null);
        await reloadFiles();
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Delete failed");
      }
    },
    [reloadFiles],
  );

  const handleRestore = useCallback(
    async (versionNo: number) => {
      if (!selectedFile) return;
      try {
        await api.restoreVersion(selectedFile.id, versionNo);
        toast.success(`Restored v${versionNo} as new version`);
        await refreshSelected(selectedFile.id);
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Restore failed");
      }
    },
    [selectedFile, refreshSelected],
  );

  const handleDownload = useCallback(
    async (file: FileEntry, versionNo?: number) => {
      try {
        await api.downloadFileVersion(file.id, versionNo);
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Download failed");
      }
    },
    [],
  );

  /* ── folder tree ──────────────────────────────────────────────── */

  const childrenOf = useMemo(() => {
    const map = new Map<number | null, Folder[]>();
    for (const f of folders) {
      const key = f.parent_id ?? null;
      map.set(key, [...(map.get(key) ?? []), f]);
    }
    return map;
  }, [folders]);

  const renderTree = useCallback(
    (parent: number | null, depth: number): React.ReactNode =>
      (childrenOf.get(parent) ?? []).map((folder) => (
        <div key={folder.id}>
          <div className="group flex items-center">
            <button
              onClick={() => setFolderId(folder.id)}
              className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg py-1.5 pr-1 text-sm transition-colors ${
                folderId === folder.id
                  ? "bg-surface-2 font-medium text-foreground"
                  : "text-muted-foreground hover:bg-surface-1 hover:text-foreground"
              }`}
              style={{ paddingLeft: `${12 + depth * 16}px` }}
            >
              {folderId === folder.id ? (
                <FolderOpen size={14} className="shrink-0" />
              ) : (
                <FolderIcon size={14} className="shrink-0" />
              )}
              <span className="truncate">{folder.name}</span>
            </button>
            <span className="mr-1 hidden shrink-0 gap-0.5 group-hover:flex">
              <button
                title="Rename folder"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleRenameFolder(folder);
                }}
                className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
              >
                <Pencil size={12} />
              </button>
              <button
                title="Delete folder"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleDeleteFolder(folder);
                }}
                className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-destructive"
              >
                <Trash2 size={12} />
              </button>
            </span>
          </div>
          {renderTree(folder.id, depth + 1)}
        </div>
      )),
    [childrenOf, folderId, handleRenameFolder, handleDeleteFolder],
  );

  /* ── render ───────────────────────────────────────────────────── */

  if (loading) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Files</h1>
          <p className="text-sm text-muted-foreground">
            Every change is versioned and audited — nothing is ever lost.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={spaceId ?? ""}
            onChange={(e) => {
              setSpaceId(Number(e.target.value));
              setFolderId(null);
              setSelectedFile(null);
            }}
            className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm"
          >
            {spaces.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} · {s.my_role}
              </option>
            ))}
          </select>
          <Button variant="outline" onClick={handleCreateSpace} title="New space">
            <Plus size={16} />
          </Button>
          {canEdit && (
            <>
              <Button variant="outline" onClick={handleNewFolder}>
                <FolderPlus size={16} className="mr-1" /> Folder
              </Button>
              <Button onClick={() => fileInputRef.current?.click()} disabled={busy}>
                {busy ? (
                  <Loader2 size={16} className="mr-1 animate-spin" />
                ) : (
                  <Upload size={16} className="mr-1" />
                )}
                Upload
              </Button>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              void handleUpload(e.target.files);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      {spaceId == null ? (
        <EmptyState
          title="No spaces yet"
          description="Create your first space to start organizing files."
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr_340px]">
          {/* Folder tree */}
          <aside className="rounded-2xl border border-border bg-surface-1 p-2">
            <button
              onClick={() => setFolderId(null)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-sm ${
                folderId === null
                  ? "bg-surface-2 font-medium text-foreground"
                  : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
              }`}
            >
              <Home size={14} /> Home
            </button>
            {folders.length > 0 && (
              <div className="mt-1 mb-1 px-3 text-[11px] uppercase tracking-wide text-muted-foreground/60">
                Folders
              </div>
            )}
            {renderTree(null, 0)}
          </aside>

          {/* File list */}
          <section
            onDragOver={(e) => {
              e.preventDefault();
              if (canEdit) setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              void handleUpload(e.dataTransfer.files);
            }}
            className={`rounded-2xl border p-4 transition-colors ${
              dragOver ? "border-primary bg-primary/5" : "border-border"
            }`}
          >
            {files.length === 0 ? (
              <EmptyState
                icon={<Upload size={28} className="text-muted-foreground" />}
                title="Nothing here yet"
                description={
                  canEdit
                    ? "Drop files here or use the Upload button."
                    : "This folder is empty."
                }
              />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="pb-2">Name</th>
                    <th className="pb-2">Size</th>
                    <th className="pb-2">Version</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr
                      key={file.id}
                      onClick={() => setSelectedFile(file)}
                      className={`cursor-pointer border-t border-border/60 transition-colors hover:bg-surface-1 ${
                        selectedFile?.id === file.id ? "bg-surface-2" : ""
                      }`}
                    >
                      <td className="py-2">
                        <span className="flex items-center gap-2">
                          <FileIcon size={15} className="text-muted-foreground" />
                          {file.name}
                        </span>
                      </td>
                      <td className="py-2 text-muted-foreground">{formatBytes(file.byte_size)}</td>
                      <td className="py-2 text-muted-foreground">v{file.current_version_no}</td>
                      <td className="py-2 text-right">
                        <span className="inline-flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              void handleDownload(file);
                            }}
                          >
                            <Download size={15} />
                          </Button>
                          {canEdit && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                void handleDelete(file);
                              }}
                            >
                              <Trash2 size={15} className="text-destructive" />
                            </Button>
                          )}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Details panel */}
          <aside className="rounded-2xl border border-border bg-surface-1 p-4">
            {!selectedFile ? (
              <p className="pt-8 text-center text-sm text-muted-foreground">
                Select a file to see its history.
              </p>
            ) : (
              <>
                <div className="mb-3 flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{selectedFile.name}</span>
                  {canEdit && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="Rename"
                      onClick={() => void handleRename()}
                    >
                      <Pencil size={14} />
                    </Button>
                  )}
                </div>
                {canEdit && (
                  <select
                    value={selectedFile.folder_id ?? ""}
                    onChange={(e) =>
                      void handleMove(e.target.value === "" ? null : Number(e.target.value))
                    }
                    className="mb-3 w-full rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-xs"
                    title="Move to folder"
                  >
                    <option value="">Home</option>
                    {folders.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                )}
                <SegmentedTabs tabs={PANEL_TABS} active={panelTab} onChange={setPanelTab} />

                {panelTab === "versions" ? (
                  <ul className="mt-4 space-y-2">
                    {versions.map((v) => (
                      <li
                        key={v.id}
                        className="flex items-center justify-between rounded-xl border border-border/60 px-3 py-2"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-medium">
                            v{v.version_no}
                            {v.version_no === selectedFile.current_version_no && (
                              <span className="ml-2 rounded-md bg-primary/10 px-1.5 py-0.5 text-[11px] text-primary">
                                current
                              </span>
                            )}
                          </div>
                          <div className="truncate text-xs text-muted-foreground">
                            {formatDate(v.created_at)}
                            {v.comment ? ` · ${v.comment}` : ""}
                          </div>
                        </div>
                        <span className="flex shrink-0 gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void handleDownload(selectedFile, v.version_no)}
                          >
                            <Download size={14} />
                          </Button>
                          {canEdit && v.version_no !== selectedFile.current_version_no && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void handleRestore(v.version_no)}
                            >
                              <RotateCcw size={14} />
                            </Button>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <ol className="mt-4 space-y-3 border-l border-border pl-4">
                    {events.map((ev) => (
                      <li key={ev.id} className="relative text-sm">
                        <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-primary" />
                        <div className="font-medium">{ev.event_type.replace(/_/g, " ")}</div>
                        <div className="text-xs text-muted-foreground">
                          {formatDate(ev.created_at)} · by {ev.actor_name ?? ev.actor_type}
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
