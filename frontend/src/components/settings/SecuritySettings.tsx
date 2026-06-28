// NOTICE: This file is protected under RCF-PL
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  AlertTriangle,
  RotateCw,
  FileCode2,
  Terminal,
  CheckCircle,
} from "lucide-react";

interface Finding {
  file: string;
  category: string;
  description: string;
  severity: string;
  line?: number;
}

interface AuditResult {
  success: boolean;
  risk_score: number;
  risk_severity: string;
  risk_recommendation: string;
  findings: Finding[];
}

export function SecuritySettings() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AuditResult | null>(null);

  const runAudit = async () => {
    setRunning(true);
    setResult(null);
    try {
      const data = await api.post<AuditResult>("/settings/security-audit");
      setResult(data);
      if (data.risk_score > 0) {
        toast.warning(`Security Audit completed. Found ${data.findings.length} issues.`);
      } else {
        toast.success("Security Audit completed successfully. All tools are safe!");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to run security audit");
    } finally {
      setRunning(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
      case "HIGH":
        return "text-[var(--color-danger)] bg-[var(--color-danger-soft)] border-[var(--color-danger)]/20";
      case "MEDIUM":
      case "WARNING":
        return "text-amber-500 bg-amber-500/10 border-amber-500/20";
      case "LOW":
        return "text-blue-500 bg-blue-500/10 border-blue-500/20";
      default:
        return "text-[var(--color-success)] bg-[var(--color-success-soft)] border-[var(--color-success)]/20";
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
      case "HIGH":
        return "border border-[var(--color-danger)]/30 text-[var(--color-danger)] bg-[var(--color-danger-soft)]";
      case "MEDIUM":
      case "WARNING":
        return "border border-amber-500/30 text-amber-500 bg-amber-500/10";
      default:
        return "border border-[var(--color-success)]/30 text-[var(--color-success)] bg-[var(--color-success-soft)]";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Shield size={16} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[var(--color-fg)]">Security & Safety</h2>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">
              Audit the security of registered agent tools and custom Python extensions using NVIDIA SkillSpector.
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={runAudit}
          disabled={running}
          className="shrink-0 flex items-center gap-1.5"
        >
          {running ? (
            <RotateCw size={13} className="animate-spin" />
          ) : (
            <Shield size={13} />
          )}
          {running ? "Scanning..." : "Run Security Audit"}
        </Button>
      </div>

      {/* Info card */}
      <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)]/40 text-xs text-[var(--color-fg-muted)] leading-relaxed space-y-2">
        <p className="font-semibold text-[var(--color-fg)] flex items-center gap-1.5">
          <Terminal size={14} className="text-[var(--color-accent)]" />
          About NVIDIA SkillSpector Security Scan
        </p>
        <p>
          SkillSpector performs static analysis checks directly on your agent tool definitions. It scans for 64 vulnerability patterns across 16 categories including:
        </p>
        <ul className="list-disc pl-5 space-y-1 mt-1 grid grid-cols-1 sm:grid-cols-2 gap-x-4">
          <li>Command injection and shell execution</li>
          <li>Data exfiltration / unauthorized network requests</li>
          <li>Privilege escalation & filesystem access</li>
          <li>Tool misuse & prompt injection risk</li>
        </ul>
      </div>

      {/* Loading state */}
      {running && (
        <div className="flex flex-col items-center justify-center py-10 border border-dashed border-[var(--color-border)] rounded-xl bg-[var(--color-surface-2)]/10 space-y-3">
          <RotateCw size={32} className="text-[var(--color-accent)] animate-spin" />
          <div className="text-center">
            <p className="text-sm font-medium text-[var(--color-fg)]">Running security analysis...</p>
            <p className="text-xs text-[var(--color-fg-muted)] mt-1">Analyzing AST and checking vulnerability patterns in backend tools</p>
          </div>
        </div>
      )}

      {/* Audit results */}
      {result && (
        <div className="space-y-6" style={{ animation: "mpIn 250ms cubic-bezier(0.16,1,0.3,1) both" }}>
          {/* Summary widgets */}
          <div className="grid gap-4 sm:grid-cols-3">
            {/* Risk Score */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 flex flex-col justify-between">
              <span className="text-xs text-[var(--color-fg-muted)] font-medium">Risk Score</span>
              <div className="mt-2 flex items-baseline gap-1">
                <span className={`text-3xl font-extrabold tracking-tight ${result.risk_score > 50 ? 'text-[var(--color-danger)]' : result.risk_score > 0 ? 'text-amber-500' : 'text-[var(--color-success)]'}`}>
                  {result.risk_score}
                </span>
                <span className="text-xs text-[var(--color-fg-muted)]">/ 100</span>
              </div>
            </div>

            {/* Risk Severity */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 flex flex-col justify-between">
              <span className="text-xs text-[var(--color-fg-muted)] font-medium">Risk Severity</span>
              <div className="mt-2 flex items-center gap-2">
                <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${getSeverityColor(result.risk_severity)}`}>
                  {result.risk_severity}
                </span>
              </div>
            </div>

            {/* Recommendation */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 flex flex-col justify-between">
              <span className="text-xs text-[var(--color-fg-muted)] font-medium">Recommendation</span>
              <div className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-[var(--color-fg)]">
                {result.risk_severity.toUpperCase() === "LOW" || result.risk_severity.toUpperCase() === "SAFE" ? (
                  <ShieldCheck size={16} className="text-[var(--color-success)] shrink-0" />
                ) : (
                  <ShieldAlert size={16} className="text-amber-500 shrink-0" />
                )}
                <span>{result.risk_recommendation}</span>
              </div>
            </div>
          </div>

          {/* Findings */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">Findings</h3>
            
            {result.findings.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 border border-[var(--color-border)] rounded-xl bg-[var(--color-surface)] space-y-2">
                <CheckCircle size={24} className="text-[var(--color-success)]" />
                <p className="text-xs font-semibold text-[var(--color-fg)]">No security issues detected</p>
                <p className="text-[10px] text-[var(--color-fg-muted)]">All python tools passed static analysis checks.</p>
              </div>
            ) : (
              <div className="rounded-xl border border-[var(--color-border)] overflow-hidden bg-[var(--color-surface)]">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-fg-muted)] font-semibold">
                        <th className="p-3">File</th>
                        <th className="p-3">Category</th>
                        <th className="p-3">Description</th>
                        <th className="p-3">Severity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {result.findings.map((finding, idx) => (
                        <tr key={idx} className="hover:bg-[var(--color-surface-2)]/50 transition-colors">
                          <td className="p-3 font-mono text-[10px] text-[var(--color-fg)] whitespace-nowrap flex items-center gap-1.5">
                            <FileCode2 size={12} className="text-[var(--color-fg-muted)] shrink-0" />
                            <span>
                              {finding.file.split("/").pop()}
                              {finding.line ? `:${finding.line}` : ""}
                            </span>
                          </td>
                          <td className="p-3 font-semibold text-[var(--color-fg)] whitespace-nowrap">
                            {finding.category}
                          </td>
                          <td className="p-3 text-[var(--color-fg-muted)] min-w-[200px]">
                            {finding.description}
                          </td>
                          <td className="p-3 whitespace-nowrap">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${getSeverityBadge(finding.severity)}`}>
                              {finding.severity}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
