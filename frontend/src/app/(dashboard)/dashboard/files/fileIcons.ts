// NOTICE: This file is protected under RCF-PL
/* File-type visuals for the workspace table: pick a lucide icon and a
   stable color per extension group so document kinds are recognizable at a
   glance. Unknown extensions fall back to a neutral file icon. */

import {
  File as NeutralFile,
  FileArchive,
  FileAudio,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileVideo,
  type LucideIcon,
} from "lucide-react";

export interface FileVisual {
  Icon: LucideIcon;
  className: string;
}

const EXT_MAP: Record<string, FileVisual> = {};

function group(exts: string[], Icon: LucideIcon, className: string): void {
  for (const ext of exts) EXT_MAP[ext] = { Icon, className };
}

group(["pdf"], FileText, "text-red-500");
group(["doc", "docx", "odt", "rtf", "txt", "md"], FileText, "text-blue-500");
group(["xls", "xlsx", "csv", "ods"], FileSpreadsheet, "text-emerald-600");
group(["ppt", "pptx", "odp"], FileText, "text-orange-500");
group(["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic"], FileImage, "text-violet-500");
group(["zip", "rar", "7z", "tar", "gz", "bz2"], FileArchive, "text-yellow-600");
group(
  ["js", "jsx", "ts", "tsx", "py", "c", "cpp", "h", "java", "go", "rs", "json", "html", "css"],
  FileCode,
  "text-cyan-600",
);
group(["mp3", "wav", "ogg", "flac"], FileAudio, "text-pink-500");
group(["mp4", "mov", "avi", "mkv", "webm"], FileVideo, "text-rose-500");

export function fileVisual(name: string): FileVisual {
  const ext = name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
  return EXT_MAP[ext] ?? { Icon: NeutralFile, className: "text-muted-foreground" };
}
