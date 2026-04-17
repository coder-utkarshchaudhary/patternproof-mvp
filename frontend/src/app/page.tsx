"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createAudit } from "@/lib/api";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const audit = await createAudit(url);
      router.push(`/audit/${audit.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start audit");
    } finally {
      setLoading(false);
    }
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

      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-2xl gap-3"
      >
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

      {error && (
        <p className="mt-4 text-sm text-red-400">{error}</p>
      )}
    </div>
  );
}
