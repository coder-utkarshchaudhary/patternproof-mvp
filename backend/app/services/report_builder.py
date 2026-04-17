"""Report builder — aggregates findings, scores, and generates summaries."""

import logging

from langchain_community.llms import Ollama

from app.agents.state import DetectedFinding
from app.core.config import settings

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are writing an executive summary for a dark pattern audit report.

Website audited: {url}
Pages analyzed: {page_count}
Total findings: {finding_count}

Breakdown by category:
{category_breakdown}

Top findings:
{top_findings}

Write a clear, professional 2-3 paragraph executive summary describing:
1. Overall assessment of the website's use of dark patterns
2. Most concerning patterns found
3. Brief recommendations

Keep it factual and objective."""


class ReportBuilder:
    def build_report(
        self,
        url: str,
        page_count: int,
        findings: list[DetectedFinding],
    ) -> dict:
        """Build a complete report from audit findings."""
        # Deduplicate
        deduped = self._deduplicate(findings)

        # Score
        score = self._calculate_score(deduped)

        # Group by category
        by_category = self._group_by_category(deduped)

        # Generate summary
        summary = self._generate_summary(url, page_count, deduped, by_category)

        return {
            "summary": summary,
            "score": score,
            "findings": deduped,
            "by_category": by_category,
        }

    def _deduplicate(self, findings: list[DetectedFinding]) -> list[DetectedFinding]:
        """Remove near-duplicate findings based on type + page."""
        seen: set[str] = set()
        unique: list[DetectedFinding] = []
        for f in findings:
            key = f"{f.dp_type}:{f.page_url}:{f.title}"
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def _calculate_score(self, findings: list[DetectedFinding]) -> int:
        """Calculate a 0-100 score (100 = clean, 0 = worst)."""
        if not findings:
            return 100

        severity_weights = {"high": 15, "medium": 8, "low": 3}
        total_penalty = sum(severity_weights.get(f.severity, 5) for f in findings)
        return max(0, 100 - total_penalty)

    def _group_by_category(
        self, findings: list[DetectedFinding]
    ) -> dict[str, list[DetectedFinding]]:
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
            for f in sorted(
                findings,
                key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.severity, 3),
            )[:5]
        )

        try:
            llm = Ollama(
                base_url=settings.ollama_base_url,
                model=settings.agent_model,
                temperature=0.3,
            )
            return llm.invoke(
                SUMMARY_PROMPT.format(
                    url=url,
                    page_count=page_count,
                    finding_count=len(findings),
                    category_breakdown=category_breakdown or "None",
                    top_findings=top_findings or "None",
                )
            )
        except Exception as e:
            logger.error("Summary generation failed: %s", e)
            if not findings:
                return f"Audit of {url} completed. No dark patterns were detected across {page_count} pages."
            return (
                f"Audit of {url} completed. Found {len(findings)} dark pattern(s) "
                f"across {page_count} pages. Categories: {', '.join(by_category.keys())}."
            )
