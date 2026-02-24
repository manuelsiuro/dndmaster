import type { TimelineEvent } from "../api";

type Props = {
  event: TimelineEvent;
};

export function TimelineCard({ event }: Props) {
  return (
    <article className={`timeline-card event-${event.event_type}`}>
      <header>
        <span className="event-type">{event.event_type.replace("_", " ")}</span>
        <time>{new Date(event.created_at).toLocaleTimeString()}</time>
      </header>
      {event.text_content && <p className="event-text">{event.text_content}</p>}
      {event.transcript_segments.length > 0 && (
        <p className="event-transcript">{event.transcript_segments[0].content}</p>
      )}
      {event.recording && <p className="event-audio">Audio clip: {event.recording.duration_ms} ms</p>}
    </article>
  );
}
