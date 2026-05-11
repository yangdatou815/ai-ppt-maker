"""Deterministic fallback for template classification.

Used when the LLM is unavailable, returns garbage, or picks a template
that's not in the registry. Heuristic: weighted keyword voting in both
English and Chinese, defaulting to ``minimal-light`` when no signal
crosses the threshold.

This is intentionally simple — the LLM is the primary classifier; this
exists so the API always returns a usable answer, never a 5xx.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_TEMPLATE = "minimal-light"


@dataclass(frozen=True)
class _Bucket:
    template: str
    en: tuple[str, ...]
    zh: tuple[str, ...]


_BUCKETS: tuple[_Bucket, ...] = (
    _Bucket(
        template="tech-blue",
        en=(
            "api", "apis", "rest", "graphql", "sdk", "kubernetes", "k8s",
            "docker", "microservice", "architecture", "latency", "throughput",
            "benchmark", "performance", "deployment", "ci/cd", "pipeline",
            "github", "git", "python", "rust", "golang", "typescript",
            "database", "schema", "infra", "infrastructure", "scalability",
            "ml", "llm", "model", "training", "inference",
        ),
        zh=(
            "架构", "技术栈", "性能", "延迟", "吞吐", "部署", "微服务",
            "数据库", "算法", "代码", "工程", "推理", "训练", "模型",
            "接口", "组件", "服务端", "前端", "后端", "集群",
        ),
    ),
    _Bucket(
        template="executive-dark",
        en=(
            "quarterly", "quarter", "q1", "q2", "q3", "q4", "revenue",
            "ebitda", "margin", "profit", "investor", "investors", "board",
            "fundraising", "valuation", "market share", "tam", "sam", "som",
            "strategy", "competitor", "competitive", "growth", "kpi",
            "earnings", "shareholder", "stakeholder", "merger", "acquisition",
        ),
        zh=(
            "营收", "利润", "毛利", "净利", "投资人", "投资者", "股东",
            "董事会", "估值", "融资", "市场份额", "战略", "竞品",
            "季度", "年报", "业绩", "增长率", "市占率", "并购",
        ),
    ),
)


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9/+\-]*", re.UNICODE)


def classify_heuristic(content: str) -> tuple[str, float, str]:
    """Return (template, confidence, reason).

    Confidence stays low (≤0.5) — this is a *fallback*, not a verdict, and
    the API marks it with ``used_fallback=True`` so the UI can surface a
    "guess" badge.
    """
    if not content:
        return DEFAULT_TEMPLATE, 0.1, "Empty input — defaulted to minimal-light."

    text_lower = content.lower()
    en_tokens = {m.group(0).lower() for m in _WORD_RE.finditer(text_lower)}

    scores: dict[str, int] = {}
    for bucket in _BUCKETS:
        s = sum(1 for t in bucket.en if t in en_tokens)
        s += sum(1 for kw in bucket.zh if kw in content)
        if s:
            scores[bucket.template] = s

    if not scores:
        return (
            DEFAULT_TEMPLATE,
            0.2,
            "No domain keywords matched — defaulted to minimal-light.",
        )

    best_template, best_score = max(scores.items(), key=lambda kv: kv[1])
    total = sum(scores.values())
    # Confidence: share of votes, capped at 0.5 because this is a heuristic.
    confidence = round(min(0.5, best_score / total * 0.5 + 0.15), 2)
    reason = (
        f"Heuristic match: {best_score} keyword(s) suggest '{best_template}'."
    )
    return best_template, confidence, reason
