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
        <div className="event-transcript">
          {event.transcript_segments.map((segment) => (
            <p key={segment.id}>{segment.content}</p>
          ))}
        </div>
      )}
      {event.recording && (
        <div className="event-audio">
          <audio controls preload="none" src={event.recording.audio_ref} />
          <small>{Math.round(event.recording.duration_ms / 1000)}s</small>
        </div>
      )}
    </article>
  );
}
