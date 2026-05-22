"""Report builder — aggregates findings, scores, and generates the summary."""

import logging

from app.agents.state import DetectedFinding
from app.services import llm

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = """You are writing the executive summary of a dark-pattern audit report used to \
certify a website's compliance with India's DPDP Act and the CCPA 2023 dark-pattern guidelines.
Write a clear, professional, factual 2-3 paragraph summary covering: (1) overall assessment, \
(2) the most concerning patterns found, (3) brief remediation recommendations. Objective tone."""


class ReportBuilder:
    def build_report(self, url: str, page_count: int, findings: list[DetectedFinding]) -> dict:
        deduped = self._deduplicate(findings)
        score = self._calculate_score(deduped)
        by_category = self._group_by_category(deduped)
        summary = self._generate_summary(url, page_count, deduped, by_category)
        return {
            "summary": summary,
            "score": score,
            "findings": deduped,
            "by_category": by_category,
        }

    def _deduplicate(self, findings: list[DetectedFinding]) -> list[DetectedFinding]:
        seen: set[str] = set()
        unique: list[DetectedFinding] = []
        for f in findings:
            key = f"{f.dp_type}:{f.page_url}:{f.title}"
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def _calculate_score(self, findings: list[DetectedFinding]) -> int:
        if not findings:
            return 100
        severity_weights = {"high": 15, "medium": 8, "low": 3}
        total_penalty = sum(severity_weights.get(f.severity, 5) for f in findings)
        return max(0, 100 - total_penalty)

    def _group_by_category(self, findings: list[DetectedFinding]) -> dict[str, list[DetectedFinding]]:
        groups: dict[str, list[DetectedFinding]] = {}
        for f in findings:
            groups.setdefault(f.category, []).append(f)
        return groups

    def _generate_summary(
        self,
        url: str,
        page_count: int,
        findings: list[DetectedFinding],
        by_category: dict[str, list[DetectedFinding]],
    ) -> str:
        category_breakdown = "\n".join(
            f"- {cat}: {len(items)} finding(s)" for cat, items in by_category.items()
        )
        top_findings = "\n".join(
            f"- [{f.severity.upper()}] {f.title}: {f.description}"
            for f in sorted(findings, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.severity, 3))[:5]
        )
        user = (
            f"Website audited: {url}\nPages analyzed: {page_count}\n"
            f"Total findings: {len(findings)}\n\n"
            f"Breakdown by category:\n{category_breakdown or 'None'}\n\n"
            f"Top findings:\n{top_findings or 'None'}"
        )
        try:
            return llm.claude_chat(SUMMARY_SYSTEM, user, max_tokens=800, temperature=0.3)
        except Exception as e:  # noqa: BLE001
            logger.error("Summary generation failed: %s", e)
            if not findings:
                return f"Audit of {url} completed. No dark patterns were detected across {page_count} pages."
            return (
                f"Audit of {url} completed. Found {len(findings)} dark pattern(s) across "
                f"{page_count} pages. Categories: {', '.join(by_category.keys())}."
            )
