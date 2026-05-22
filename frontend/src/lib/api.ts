const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Audit {
  id: number;
  url: string;
  status: string;
  progress_message: string | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface Finding {
  id: number;
  page_id: number | null;
  category: string;
  dp_type: string;
  ccpa_pattern: string | null;
  severity: string;
  title: string;
  description: string;
  explanation: string | null;
  evidence_screenshot_path: string | null;
  page_url: string | null;
  bounding_box: Record<string, number> | null;
  confidence_score: number | null;
  is_dynamic: boolean;
}

export interface ReportReference {
  title: string;
  url: string;
  snippet: string | null;
}

export interface Report {
  id: number;
  audit_id: number;
  summary: string;
  score: number;
  pdf_path: string | null;
  references: ReportReference[];
  generated_at: string;
  findings: Finding[];
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

export function createAudit(url: string): Promise<Audit> {
  return apiFetch("/api/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export function listAudits(): Promise<Audit[]> {
  return apiFetch("/api/audits");
}

export function getAudit(id: number): Promise<Audit> {
  return apiFetch(`/api/audits/${id}`);
}

export function getReport(auditId: number): Promise<Report> {
  return apiFetch(`/api/audits/${auditId}/report`);
}

export function reportPdfUrl(auditId: number): string {
  return `${API_BASE}/api/audits/${auditId}/report/pdf`;
}
