"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createJob } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lookupKey, setLookupKey] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const job = await createJob(url);
      router.push(`/job/${job.job_key}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start audit");
    } finally {
      setLoading(false);
    }
  }

  function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    const key = lookupKey.trim();
    if (key) router.push(`/job/${key}`);
  }

  return (
    <div className="flex flex-col items-center justify-center px-4 py-24">
      <h1 className="mb-4 text-5xl font-extrabold tracking-tight">
        Audit any website for{" "}
        <span className="text-indigo-400">dark patterns</span>
      </h1>
      <p className="mb-10 max-w-xl text-center text-lg text-zinc-400">
        Enter a URL and get a comprehensive report identifying deceptive design
        patterns — hidden costs, fake urgency, confirmshaming, and more.
      </p>

      <form onSubmit={handleSubmit} className="flex w-full max-w-2xl gap-3">
        <input
          type="url"
          required
          placeholder="https://example.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-3 text-base text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {loading ? "Starting…" : "Start Audit"}
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-16 w-full max-w-2xl border-t border-zinc-800 pt-10">
        <p className="mb-3 text-sm font-medium text-zinc-400">
          Already have a job key?
        </p>
        <form onSubmit={handleLookup} className="flex gap-3">
          <input
            type="text"
            placeholder="Enter job key (e.g. 42)"
            value={lookupKey}
            onChange={(e) => setLookupKey(e.target.value)}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <button
            type="submit"
            className="rounded-lg border border-zinc-600 px-5 py-2.5 text-sm font-medium text-zinc-300 transition hover:border-zinc-500 hover:text-white"
          >
            Track Job
          </button>
        </form>
      </div>
    </div>
  );
}
