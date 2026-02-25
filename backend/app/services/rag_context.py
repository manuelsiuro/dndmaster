from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import NarrativeMemoryType, NarrativeSummary, TimelineEvent
from app.services.embedding import hash_text_embedding
from app.services.memory_store import MemorySearchMatch, search_memory_chunks


@dataclass(slots=True)
class OrchestrationContextBundle:
    query_embedding: list[float]
    retrieved_memory: list[MemorySearchMatch]
    summaries: list[NarrativeSummary]
    timeline_events: list[TimelineEvent]
    prompt_context: str


def _event_text(event: TimelineEvent) -> str:
    if event.text_content and event.text_content.strip():
        return event.text_content.strip()
    for transcript in sorted(event.transcripts, key=lambda item: item.timestamp):
        if transcript.content.strip():
            return transcript.content.strip()
    return "(no text)"


def _build_prompt_context(
    *,
    query_text: str,
    retrieved_memory: Sequence[MemorySearchMatch],
    summaries: Sequence[NarrativeSummary],
    timeline_events: Sequence[TimelineEvent],
) -> str:
    lines = [f"User query: {query_text.strip()}", ""]

    lines.append("Retrieved memory:")
    if retrieved_memory:
        for index, item in enumerate(retrieved_memory, start=1):
            chunk = item.chunk
            lines.append(
                f"{index}. [{chunk.memory_type.value}] "
                f"(similarity={item.similarity:.3f}) {chunk.content.strip()}"
            )
    else:
        lines.append("none")
    lines.append("")

    lines.append("Recent summaries:")
    if summaries:
        for index, summary in enumerate(summaries, start=1):
            snippet = summary.summary_text.strip()[:600]
            lines.append(f"{index}. [{summary.summary_window}] {snippet}")
    else:
        lines.append("none")
    lines.append("")

    lines.append("Recent timeline events:")
    if timeline_events:
        for index, event in enumerate(timeline_events, start=1):
            lines.append(
                f"{index}. [{event.event_type.value}] "
                f"{_event_text(event)}"
            )
    else:
        lines.append("none")

    return "\n".join(lines).strip()


async def build_orchestration_context(
    db: AsyncSession,
    *,
    story_id: str,
    query_text: str,
    embedding_dimensions: int,
    memory_limit: int,
    summary_limit: int,
    timeline_limit: int,
    memory_types: Sequence[NarrativeMemoryType] | None = None,
) -> OrchestrationContextBundle:
    query_embedding = hash_text_embedding(query_text, embedding_dimensions)
    retrieved_memory = await search_memory_chunks(
        db,
        story_id=story_id,
        query_embedding=query_embedding,
        limit=memory_limit,
        memory_types=memory_types,
    )

    summaries: list[NarrativeSummary] = []
    if summary_limit > 0:
        summaries_result = await db.scalars(
            select(NarrativeSummary)
            .where(NarrativeSummary.story_id == story_id)
            .order_by(NarrativeSummary.created_at.desc())
            .limit(summary_limit)
        )
        summaries = list(summaries_result.all())

    timeline_events: list[TimelineEvent] = []
    if timeline_limit > 0:
        timeline_result = await db.scalars(
            select(TimelineEvent)
            .where(TimelineEvent.story_id == story_id)
            .options(selectinload(TimelineEvent.transcripts))
            .order_by(TimelineEvent.created_at.desc())
            .limit(timeline_limit)
        )
        timeline_events = list(timeline_result.all())

    prompt_context = _build_prompt_context(
        query_text=query_text,
        retrieved_memory=retrieved_memory,
        summaries=summaries,
        timeline_events=timeline_events,
    )
    return OrchestrationContextBundle(
        query_embedding=query_embedding,
        retrieved_memory=retrieved_memory,
        summaries=summaries,
        timeline_events=timeline_events,
        prompt_context=prompt_context,
    )
