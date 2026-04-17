"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getAudit, getReport, type Audit, type Report } from "@/lib/api";

export default function AuditPage() {
  const params = useParams();
  const auditId = Number(params.id);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auditId) return;

    const poll = setInterval(async () => {
      try {
        const a = await getAudit(auditId);
        setAudit(a);
        if (a.status === "completed") {
          clearInterval(poll);
          const r = await getReport(auditId);
          setReport(r);
        } else if (a.status === "failed") {
          clearInterval(poll);
        }
      } catch {
        setError("Failed to fetch audit status");
        clearInterval(poll);
      }
    }, 2000);

    // Initial fetch
    getAudit(auditId).then(setAudit).catch(() => setError("Audit not found"));

    return () => clearInterval(poll);
  }, [auditId]);

  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-400">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="mb-2 text-3xl font-bold">Audit #{audit.id}</h1>
      <p className="mb-1 text-zinc-400 break-all">{audit.url}</p>

      {/* Status */}
      <div className="mb-8 mt-4 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <div className="flex items-center gap-3">
          <StatusBadge status={audit.status} />
          <span className="text-sm text-zinc-400">
            {audit.progress_message ?? statusLabel(audit.status)}
          </span>
        </div>
        {audit.status === "failed" && audit.error_message && (
          <p className="mt-2 text-sm text-red-400">{audit.error_message}</p>
        )}
      </div>

      {/* Report */}
      {report && (
        <div>
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-bold">Report</h2>
            <div className="flex items-center gap-2">
              <span className="text-4xl font-extrabold text-indigo-400">
                {report.score}
              </span>
              <span className="text-sm text-zinc-400">/ 100</span>
            </div>
          </div>

          <p className="mb-6 text-zinc-300">{report.summary}</p>

          <h3 className="mb-4 text-xl font-semibold">
            Findings ({report.findings.length})
          </h3>
          <div className="space-y-4">
            {report.findings.map((f) => (
              <div
                key={f.id}
                className="rounded-lg border border-zinc-800 bg-zinc-900 p-4"
              >
                <div className="mb-2 flex items-center gap-2">
                  <SeverityBadge severity={f.severity} />
                  <span className="font-semibold">{f.title}</span>
                  <span className="ml-auto text-xs text-zinc-500">
                    {f.category} / {f.dp_type}
                  </span>
                </div>
                <p className="text-sm text-zinc-300">{f.description}</p>
                {f.explanation && (
                  <p className="mt-2 text-sm text-zinc-400">{f.explanation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-yellow-900 text-yellow-300",
    crawling: "bg-blue-900 text-blue-300",
    analyzing: "bg-purple-900 text-purple-300",
    generating_report: "bg-indigo-900 text-indigo-300",
    completed: "bg-green-900 text-green-300",
    failed: "bg-red-900 text-red-300",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-zinc-800 text-zinc-400"}`}
    >
      {status}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    low: "bg-yellow-900 text-yellow-300",
    medium: "bg-orange-900 text-orange-300",
    high: "bg-red-900 text-red-300",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[severity] ?? "bg-zinc-800"}`}
    >
      {severity}
    </span>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "Waiting in queue…",
    crawling: "Crawling website…",
    analyzing: "Analyzing for dark patterns…",
    generating_report: "Generating report…",
    completed: "Audit complete",
    failed: "Audit failed",
  };
  return labels[status] ?? status;
}
