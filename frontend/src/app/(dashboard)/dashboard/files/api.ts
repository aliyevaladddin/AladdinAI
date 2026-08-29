// NOTICE: This file is protected under RCF-PL
/* Typed API surface for the Files workspace page.
   JSON calls go through lib/api.ts (`api` object — auth header, 401 refresh,
   SWR-style cache). List reads bypass the cache so the UI shows fresh state
   right after a mutation. Downloads stream the blob directly. */

import { API_URL, api } from "@/lib/api";
import type {
  FileEntry,
  FileEvent,
  FileVersion,
  Folder,
  Space,
} from "./types";

/* ── Spaces ─────────────────────────────────────────────────────── */

export function listSpaces(): Promise<Space[]> {
  return api.get<Space[]>("/spaces", { bypassCache: true });
}

export function createSpace(name: string): Promise<Space> {
  return api.post<Space>("/spaces", { name });
}

export function renameSpace(spaceId: number, name: string): Promise<Space> {
  return api.patch<Space>(`/spaces/${spaceId}`, { name });
}

export async function deleteSpace(spaceId: number): Promise<void> {
  await api.delete(`/spaces/${spaceId}`);
}

/* ── Folders ────────────────────────────────────────────────────── */

export function listFolders(spaceId: number): Promise<Folder[]> {
  return api.get<Folder[]>(`/spaces/${spaceId}/folders`, { bypassCache: true });
}

export function createFolder(
  spaceId: number,
  name: string,
  parentId: number | null,
): Promise<Folder> {
  return api.post<Folder>(`/spaces/${spaceId}/folders`, {
    name,
    parent_id: parentId,
  });
}

export function renameFolder(folderId: number, name: string): Promise<Folder> {
  return api.patch<Folder>(`/folders/${folderId}`, { name });
}

export function deleteFolder(folderId: number): Promise<void> {
  return api.delete(`/folders/${folderId}`);
}

/* ── Files ──────────────────────────────────────────────────────── */

export function listFiles(spaceId: number, folderId?: number | null): Promise<FileEntry[]> {
  // Root asks explicitly for loose files — otherwise the API returns everything.
  const query = folderId != null ? `?folder_id=${folderId}` : "?root=true";
  return api.get<FileEntry[]>(`/spaces/${spaceId}/files${query}`, { bypassCache: true });
}

export function uploadFile(
  spaceId: number,
  file: File,
  folderId: number | null,
  comment?: string,
): Promise<FileEntry> {
  const fields: Record<string, string> = {};
  if (folderId != null) fields.folder_id = String(folderId);
  if (comment) fields.comment = comment;
  return api.upload<FileEntry>(`/spaces/${spaceId}/files/upload`, file, fields);
}

export function uploadNewVersion(fileId: number, file: File, comment?: string): Promise<FileVersion> {
  const fields = comment ? { comment } : undefined;
  return api.upload<FileVersion>(`/files/${fileId}/upload_version`, file, fields);
}

export function restoreVersion(fileId: number, versionNo: number): Promise<FileVersion> {
  return api.post<FileVersion>(`/files/${fileId}/restore`, { version_no: versionNo });
}

export function moveFile(fileId: number, folderId: number | null): Promise<FileEntry> {
  return api.patch<FileEntry>(`/files/${fileId}/move`, { folder_id: folderId });
}

export function renameFile(fileId: number, name: string): Promise<FileEntry> {
  return api.patch<FileEntry>(`/files/${fileId}`, { name });
}

export async function deleteFile(fileId: number): Promise<void> {
  await api.delete(`/files/${fileId}`);
}

export function listVersions(fileId: number): Promise<FileVersion[]> {
  return api.get<FileVersion[]>(`/files/${fileId}/versions`, { bypassCache: true });
}

export function listEvents(fileId: number): Promise<FileEvent[]> {
  return api.get<FileEvent[]>(`/files/${fileId}/events`, { bypassCache: true });
}

/* ── Content (text preview for .wrt viewer) ─────────────────────── */

export async function getFileContent(
  fileId: number,
  versionNo?: number,
): Promise<{ content: string; name: string; version_no: number }> {
  const query = versionNo != null ? `?version=${versionNo}` : "";
  return api.get<{ content: string; name: string; version_no: number }>(
    `/files/${fileId}/content${query}`,
    { bypassCache: true },
  );
}

/* ── Download (blob → browser save dialog) ──────────────────────── */

export async function downloadFileVersion(fileId: number, versionNo?: number): Promise<void> {
  const query = versionNo != null ? `?version=${versionNo}` : "";
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_URL}/files/${fileId}/download${query}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = match?.[1] ?? "download";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
