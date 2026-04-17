"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listAudits, type Audit } from "@/lib/api";

export default function HistoryPage() {
  const [audits, setAudits] = useState<Audit[]>([]);

  useEffect(() => {
    listAudits().then(setAudits);
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="mb-6 text-3xl font-bold">Audit History</h1>
      {audits.length === 0 ? (
        <p className="text-zinc-400">No audits yet.</p>
      ) : (
        <div className="space-y-3">
          {audits.map((a) => (
            <Link
              key={a.id}
              href={`/audit/${a.id}`}
              className="block rounded-lg border border-zinc-800 bg-zinc-900 p-4 transition hover:border-zinc-600"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium break-all">{a.url}</span>
                <span className="text-xs text-zinc-500">
                  {new Date(a.created_at).toLocaleString()}
                </span>
              </div>
              <span className="mt-1 inline-block rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                {a.status}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
