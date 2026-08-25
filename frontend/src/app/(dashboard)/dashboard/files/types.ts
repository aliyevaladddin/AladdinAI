// NOTICE: This file is protected under RCF-PL

export type SpaceRole = "owner" | "editor" | "viewer";

export interface Space {
  id: number;
  name: string;
  created_by_user_id: number;
  my_role: SpaceRole;
  created_at: string;
}

export interface SpaceMember {
  user_id: number;
  email: string;
  name: string | null;
  role: SpaceRole;
}

export interface Folder {
  id: number;
  space_id: number;
  parent_id: number | null;
  name: string;
  created_at: string;
}

export interface FileEntry {
  id: number;
  space_id: number;
  folder_id: number | null;
  name: string;
  mime_type: string | null;
  byte_size: number;
  current_version_no: number;
  created_by_user_id: number;
  deleted_at: string | null;
  created_at: string;
}

export interface FileVersion {
  id: number;
  file_id: number;
  version_no: number;
  byte_size: number;
  uploader_user_id: number;
  author_type: "human" | "agent";
  agent_run_id: number | null;
  comment: string | null;
  created_at: string;
}

export type FileEventType =
  | "created"
  | "version_added"
  | "downloaded"
  | "restored"
  | "moved"
  | "renamed"
  | "deleted";

export interface FileEvent {
  id: number;
  file_id: number;
  event_type: FileEventType;
  actor_type: "human" | "agent" | "system";
  actor_user_id: number | null;
  /** Display name resolved server-side; null for system events. */
  actor_name?: string | null;
  payload: string | null;
  created_at: string;
}
