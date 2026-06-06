import { type ReactNode } from "react";
import packageJson from "../../../package.json";

export interface StatusItem {
  id: string;
  dot?: "ok" | "amber" | "info" | "violet";
  label: ReactNode;
  /** Monospaced detail next to the label, e.g. "14ms". */
  code?: string;
  /** Right-side group flag — pushed past the spacer. */
  right?: boolean;
  /** Tinted text variant — used for the RCF row. */
  variant?: "default" | "rcf";
}

interface StatusBarProps {
  items?: StatusItem[];
  /** Custom element rendered between the spacer and the right-aligned items. */
  rightExtra?: ReactNode;
}

const DEFAULT_ITEMS: StatusItem[] = [
  { id: "orch",     dot: "ok",     label: "Orchestrator", code: "up" },
  { id: "pg",       dot: "ok",     label: "Postgres",     code: "ready" },
  { id: "mongo",    dot: "ok",     label: "Mongo",        code: "ready" },
  { id: "nim",      dot: "info",   label: "NIM",          code: "research" },
  { id: "rcf",      dot: "violet", label: "RCF",          code: "chain", variant: "rcf" },
  { id: "version",  right: true,   label: "aladdin-ai",   code: `v${packageJson.version}` },
];

export function StatusBar({ items = DEFAULT_ITEMS, rightExtra }: StatusBarProps) {
  const left  = items.filter((i) => !i.right);
  const right = items.filter((i) =>  i.right);

  return (
    <footer className="statusbar" aria-label="System status">
      {left.map((item) => (
        <StatusEntry key={item.id} item={item} />
      ))}
      <span className="sb-spacer" />
      {rightExtra}
      {right.map((item) => (
        <StatusEntry key={item.id} item={item} />
      ))}
    </footer>
  );
}

function StatusEntry({ item }: { item: StatusItem }) {
  return (
    <div className={`sb-item${item.variant === "rcf" ? " rcf" : ""}`}>
      {item.dot && <span className={`d ${item.dot}`} aria-hidden="true" />}
      <span>{item.label}</span>
      {item.code && <code>{item.code}</code>}
    </div>
  );
}
