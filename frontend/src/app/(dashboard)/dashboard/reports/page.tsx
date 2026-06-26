// NOTICE: This file is protected under RCF-PL
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { API_URL } from "@/lib/api";

type ReportType = "all" | "deals" | "contacts" | "activities";

interface ReportCard {
  type: ReportType;
  title: string;
  description: string;
  icon: string;
  color: string;
}

const REPORTS: ReportCard[] = [
  {
    type: "contacts",
    title: "Contacts Report",
    description: "All CRM contacts with email, phone, company, tags and source.",
    icon: "👥",
    color: "#3B82F6",
  },
  {
    type: "deals",
    title: "Deals Report",
    description: "Pipeline deals with stage, amount, currency and probability. Includes total sum row.",
    icon: "💼",
    color: "#10B981",
  },
  {
    type: "activities",
    title: "Activities Report",
    description: "All communication activities: emails, messages, calls by channel.",
    icon: "📋",
    color: "#8B5CF6",
  },
  {
    type: "all",
    title: "Full Report",
    description: "Complete multi-sheet workbook: Contacts + Deals + Activities in one file.",
    icon: "📊",
    color: "#F59E0B",
  },
];

export default function ReportsPage() {
  const [downloading, setDownloading] = useState<ReportType | null>(null);

  const handleDownload = async (type: ReportType) => {
    setDownloading(type);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/reports/excel?type=${type}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Download failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aladdinai_${type}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Report download error:", e);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Reports</h2>
        <p className="text-sm mt-1" style={{ color: "var(--color-fg-muted)" }}>
          Download styled Excel reports for your CRM data
        </p>
      </div>

      {/* Report cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {REPORTS.map((r) => {
          const isLoading = downloading === r.type;
          return (
            <div
              key={r.type}
              id={`report-card-${r.type}`}
              className="group flex flex-col gap-4 rounded-2xl border p-5 transition-all hover:shadow-md"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              {/* Icon + title */}
              <div className="flex items-start gap-3">
                <div
                  className="flex items-center justify-center w-10 h-10 rounded-xl text-xl shrink-0"
                  style={{ background: `${r.color}18` }}
                >
                  {r.icon}
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-sm">{r.title}</p>
                  <p className="text-xs mt-0.5 leading-relaxed" style={{ color: "var(--color-fg-muted)" }}>
                    {r.description}
                  </p>
                </div>
              </div>

              {/* Metadata tags */}
              <div className="flex flex-wrap gap-1.5">
                {r.type !== "all" ? (
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full border"
                    style={{
                      borderColor: r.color + "44",
                      color: r.color,
                      background: r.color + "11",
                    }}
                  >
                    {r.type.charAt(0).toUpperCase() + r.type.slice(1)}
                  </span>
                ) : (
                  ["Contacts", "Deals", "Activities"].map((s) => (
                    <span
                      key={s}
                      className="text-[10px] px-2 py-0.5 rounded-full border"
                      style={{
                        borderColor: "var(--color-border)",
                        color: "var(--color-fg-muted)",
                        background: "var(--color-surface-2)",
                      }}
                    >
                      {s}
                    </span>
                  ))
                )}
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full border ml-auto"
                  style={{
                    borderColor: "var(--color-border)",
                    color: "var(--color-fg-muted)",
                    background: "var(--color-surface-2)",
                  }}
                >
                  .xlsx
                </span>
              </div>

              {/* Download button */}
              <Button
                id={`download-report-${r.type}`}
                variant="outline"
                size="sm"
                className="w-full"
                disabled={isLoading}
                onClick={() => handleDownload(r.type)}
                style={
                  isLoading
                    ? {}
                    : {
                        borderColor: r.color + "55",
                        color: r.color,
                      }
                }
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span
                      className="w-3.5 h-3.5 border-2 border-t-transparent rounded-full animate-spin inline-block"
                      style={{ borderColor: r.color, borderTopColor: "transparent" }}
                    />
                    Generating…
                  </span>
                ) : (
                  "⬇ Download Excel"
                )}
              </Button>
            </div>
          );
        })}
      </div>

      {/* Info footer */}
      <div
        className="mt-8 rounded-xl border px-4 py-3 text-xs"
        style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-2)",
          color: "var(--color-fg-muted)",
        }}
      >
        Reports include styled headers, alternating row colors, frozen header rows and summary totals.
        Files are generated in real-time from your current CRM data.
      </div>
    </div>
  );
}
