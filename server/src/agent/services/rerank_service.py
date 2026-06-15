"""Business service for reranking retrieval hits."""

from __future__ import annotations

from agent.components.factories import create_reranker
from agent.config import get_settings


class RerankService:
    """Apply a lightweight reranking policy to candidate chunks."""

    def rerank(self, question: str, hits: list[dict], top_n: int | None = None) -> list[dict]:
        """Sort hits with a cross-encoder when available, else use lexical fallback."""

        reranker = create_reranker()
        if reranker is not None and hits:
            try:
                pairs = [(question, hit.get("content", "")) for hit in hits]
                scores = reranker.score(pairs)
                scored_hits: list[dict] = []
                for hit, score in zip(hits, scores):
                    scored_hits.append({**hit, "rerank_score": float(score)})
                reranked = sorted(
                    scored_hits,
                    key=lambda hit: (hit.get("rerank_score", 0.0), hit.get("score", 0.0)),
                    reverse=True,
                )
                limit = top_n or get_settings().rerank_top_n
                return reranked[:limit]
            except Exception:
                pass
        query_terms = {term for term in question.lower().split() if term}
        reranked = sorted(
            hits,
            key=lambda hit: (
                self._overlap(query_terms, hit.get("content", "")),
                hit.get("score", 0.0),
            ),
            reverse=True,
        )
        limit = top_n or get_settings().rerank_top_n
        return reranked[:limit]

    def _overlap(self, query_terms: set[str], content: str) -> int:
        """Return a simple lexical overlap count."""

        content_terms = set(content.lower().split())
        return len(query_terms & content_terms)
