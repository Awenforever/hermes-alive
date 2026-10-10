"""Explainable retrieval over authorized Alive memory records.

BM25 handles lexical relevance; reciprocal-rank fusion combines independent
relevance, importance, recency, and authority orderings without pretending
their raw scales are interchangeable.  The module receives already-authorized
and decrypted records from ``MemoryProjection`` and persists no plaintext.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
import re
from typing import Iterable, Sequence

from .memory import MemoryAuthority, MemoryRecord


_LATIN_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
_RRF_K = 60
_MAX_SEARCH_TEXT = 32_000


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    record: MemoryRecord
    score: float
    component_ranks: tuple[tuple[str, int], ...]
    matched_terms: tuple[str, ...]

    @property
    def explanation(self) -> str:
        ranks = ", ".join(f"{name}=#{rank}" for name, rank in self.component_ranks)
        terms = ", ".join(self.matched_terms) if self.matched_terms else "no query"
        return f"RRF({ranks}); matched: {terms}"


def _tokens(text: str) -> tuple[str, ...]:
    normalized = str(text).casefold()
    values = list(_LATIN_TOKEN_RE.findall(normalized))
    for run in _CJK_RE.findall(normalized):
        if len(run) == 1:
            values.append(run)
        else:
            values.extend(run[index : index + 2] for index in range(len(run) - 1))
    return tuple(values)


def _search_text(record: MemoryRecord) -> str:
    value = json.dumps(
        record.value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{record.kind.value} {record.predicate} {value}"[:_MAX_SEARCH_TEXT]


def _rank(values: Iterable[tuple[str, object]], *, reverse: bool) -> dict[str, int]:
    ordered = sorted(values, key=lambda item: (item[1], item[0]), reverse=reverse)
    return {memory_id: index for index, (memory_id, _value) in enumerate(ordered, start=1)}


def _bm25(
    records: Sequence[MemoryRecord], query_tokens: tuple[str, ...]
) -> tuple[dict[str, float], dict[str, tuple[str, ...]]]:
    documents = {record.memory_id: Counter(_tokens(_search_text(record))) for record in records}
    lengths = {memory_id: sum(counts.values()) for memory_id, counts in documents.items()}
    average_length = sum(lengths.values()) / max(len(lengths), 1)
    query_terms = tuple(dict.fromkeys(query_tokens))
    document_frequency = {
        term: sum(1 for counts in documents.values() if term in counts)
        for term in query_terms
    }
    scores: dict[str, float] = {}
    matches: dict[str, tuple[str, ...]] = {}
    for memory_id, counts in documents.items():
        matched = tuple(term for term in query_terms if counts.get(term, 0) > 0)
        matches[memory_id] = matched
        score = 0.0
        for term in matched:
            frequency = counts[term]
            frequency_docs = document_frequency[term]
            inverse_frequency = math.log(
                1.0 + (len(documents) - frequency_docs + 0.5) / (frequency_docs + 0.5)
            )
            denominator = frequency + 1.2 * (
                1.0 - 0.75 + 0.75 * lengths[memory_id] / max(average_length, 1.0)
            )
            score += inverse_frequency * frequency * 2.2 / denominator
        scores[memory_id] = score
    return scores, matches


_AUTHORITY_ORDER = {
    MemoryAuthority.USER_EXPLICIT: 5,
    MemoryAuthority.SYSTEM_MIGRATION: 4,
    MemoryAuthority.DIRECT_OBSERVATION: 3,
    MemoryAuthority.REFLECTION: 2,
    MemoryAuthority.MODEL_INFERENCE: 1,
}


def rank_records(
    records: Sequence[MemoryRecord],
    query: str = "",
    *,
    limit: int = 20,
) -> list[RetrievalHit]:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    query_tokens = _tokens(query)
    lexical_scores, matches = _bm25(records, query_tokens)
    candidates = [
        record
        for record in records
        if not query_tokens or lexical_scores.get(record.memory_id, 0.0) > 0.0
    ]
    if not candidates:
        return []

    components: dict[str, dict[str, int]] = {}
    if query_tokens:
        components["relevance"] = _rank(
            ((record.memory_id, lexical_scores[record.memory_id]) for record in candidates),
            reverse=True,
        )
    components["importance"] = _rank(
        ((record.memory_id, record.importance) for record in candidates), reverse=True
    )
    components["recency"] = _rank(
        ((record.memory_id, record.updated_at.timestamp()) for record in candidates),
        reverse=True,
    )
    components["authority"] = _rank(
        ((record.memory_id, _AUTHORITY_ORDER[record.authority]) for record in candidates),
        reverse=True,
    )

    hits: list[RetrievalHit] = []
    for record in candidates:
        ranks = tuple((name, ranking[record.memory_id]) for name, ranking in components.items())
        score = sum(1.0 / (_RRF_K + rank) for _name, rank in ranks)
        hits.append(
            RetrievalHit(
                record=record,
                score=score,
                component_ranks=ranks,
                matched_terms=matches.get(record.memory_id, ()),
            )
        )
    hits.sort(key=lambda hit: (-hit.score, hit.record.memory_id))
    return hits[:limit]
