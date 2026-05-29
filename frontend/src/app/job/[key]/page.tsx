"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getJobStatus, type JobStatus } from "@/lib/api";

export default function JobPage() {
  const params = useParams();
  const key = String(params.key);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getJobStatus(key);
      setJob(data);
      return data.status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch job status");
      return "failed";
    }
  }, [key]);

  useEffect(() => {
    if (!key) return;

    fetchStatus();

    const interval = setInterval(async () => {
      const status = await fetchStatus();
      if (status === "done" || status === "failed") {
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [key, fetchStatus]);

  function copyKey() {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-400">Loading job status…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="mb-3 flex items-center gap-3">
          <JobStatusBadge status={job.status} />
          <span className="text-sm text-zinc-500">
            {job.status === "processing" && "Refreshing every 3s…"}
            {job.status === "done" && `Completed ${formatTime(job.completed_at)}`}
            {job.status === "failed" && `Failed ${formatTime(job.completed_at)}`}
          </span>
        </div>

        <h1 className="mb-1 text-2xl font-bold">Job Tracker</h1>
        <p className="mb-3 break-all text-zinc-400 text-sm">{job.url}</p>

        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Job key:</span>
          <code className="rounded bg-zinc-800 px-2 py-0.5 text-sm font-mono text-indigo-300">
            {job.job_key}
          </code>
          <button
            onClick={copyKey}
            className="rounded px-2 py-0.5 text-xs text-zinc-400 transition hover:text-white"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>

      {/* Current progress message */}
      {job.progress_message && (
        <div className="mb-6 rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3">
          <p className="text-sm text-zinc-300">
            <span className="mr-2 text-zinc-500">Current step:</span>
            {job.progress_message}
          </p>
        </div>
      )}

      {/* Error */}
      {job.status === "failed" && job.error_message && (
        <div className="mb-6 rounded-lg border border-red-900 bg-red-950/40 px-4 py-3">
          <p className="text-sm font-medium text-red-400">Error</p>
          <p className="mt-1 text-sm text-red-300">{job.error_message}</p>
        </div>
      )}

      {/* Live summary */}
      {job.summary_md && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-500">
            Live Progress Summary
          </h2>
          <MarkdownView content={job.summary_md} />
        </div>
      )}

      {/* Done — link to full audit results */}
      {job.status === "done" && (
        <div className="mt-6 rounded-lg border border-indigo-800 bg-indigo-950/40 p-4 text-center">
          <p className="mb-3 text-sm text-indigo-300">Audit complete! View the full report:</p>
          <a
            href={`/audit/${job.job_key}`}
            className="inline-block rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            View Full Report →
          </a>
        </div>
      )}
    </div>
  );
}

function JobStatusBadge({ status }: { status: JobStatus["status"] }) {
  const styles = {
    processing: "bg-yellow-900/60 text-yellow-300 border-yellow-800",
    done: "bg-green-900/60 text-green-300 border-green-800",
    failed: "bg-red-900/60 text-red-300 border-red-800",
  };
  const labels = {
    processing: "⟳ Processing",
    done: "✓ Done",
    failed: "✗ Failed",
  };
  return (
    <span
      className={`rounded-full border px-3 py-0.5 text-xs font-semibold tracking-wide ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return "";
  }
}

// Simple inline markdown renderer — handles headings, bold, lists, blockquotes.
function MarkdownView({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <div className="space-y-1 text-sm">
      {lines.map((line, i) => {
        if (line.startsWith("# ")) {
          return (
            <h1 key={i} className="mt-4 text-lg font-bold text-zinc-100">
              {line.slice(2)}
            </h1>
          );
        }
        if (line.startsWith("## ")) {
          return (
            <h2 key={i} className="mt-4 text-base font-semibold text-zinc-200">
              {line.slice(3)}
            </h2>
          );
        }
        if (line.startsWith("### ")) {
          return (
            <h3 key={i} className="mt-3 text-sm font-semibold text-zinc-300">
              {line.slice(4)}
            </h3>
          );
        }
        if (line.startsWith("> ")) {
          return (
            <blockquote key={i} className="border-l-2 border-indigo-600 pl-3 italic text-zinc-400">
              {renderInline(line.slice(2))}
            </blockquote>
          );
        }
        if (line.startsWith("- ")) {
          return (
            <div key={i} className="flex gap-2 pl-2 text-zinc-300">
              <span className="mt-0.5 text-zinc-600">•</span>
              <span>{renderInline(line.slice(2))}</span>
            </div>
          );
        }
        if (line.startsWith("  _") && line.endsWith("_")) {
          return (
            <p key={i} className="pl-6 text-xs italic text-zinc-500">
              {line.slice(3, -1)}
            </p>
          );
        }
        if (line.startsWith("```") || line === "```") {
          return null;
        }
        if (line === "") {
          return <div key={i} className="h-2" />;
        }
        return (
          <p key={i} className="text-zinc-300 leading-relaxed">
            {renderInline(line)}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string): React.ReactNode {
  // Handle **bold** and `code` inline.
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(
        <strong key={match.index} className="font-semibold text-zinc-100">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("`")) {
      parts.push(
        <code key={match.index} className="rounded bg-zinc-800 px-1 font-mono text-xs text-indigo-300">
          {token.slice(1, -1)}
        </code>
      );
    }
    last = match.index + token.length;
  }

  if (last < text.length) {
    parts.push(text.slice(last));
  }

  return parts.length === 1 && typeof parts[0] === "string" ? parts[0] : <>{parts}</>;
}
