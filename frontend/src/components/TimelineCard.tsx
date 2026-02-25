import type { TimelineEvent } from "../api";

type Props = {
  event: TimelineEvent;
  replayFocused?: boolean;
  onReplayTurn?: (turnId: string) => void;
};

function formatTurnLabel(turnId: string): string {
  if (turnId.length <= 16) {
    return turnId;
  }
  return `${turnId.slice(0, 8)}...${turnId.slice(-6)}`;
}

export function TimelineCard({ event, replayFocused = false, onReplayTurn }: Props) {
  return (
    <article
      className={`timeline-card event-${event.event_type}${replayFocused ? " timeline-card-focus" : ""}`}
    >
      <header>
        <span className="event-type">{event.event_type.replace("_", " ")}</span>
        <div className="timeline-header-meta">
          <small className="turn-tag">Turn {formatTurnLabel(event.turn_id)}</small>
          <time>{new Date(event.created_at).toLocaleTimeString()}</time>
        </div>
      </header>
      {(event.source_event_id || onReplayTurn) && (
        <div className="event-links">
          {event.source_event_id && <small>Source: {event.source_event_id.slice(0, 8)}</small>}
          {onReplayTurn && (
            <button type="button" onClick={() => onReplayTurn(event.turn_id)}>
              Replay turn
            </button>
          )}
        </div>
      )}
      {event.text_content && <p className="event-text">{event.text_content}</p>}
      {event.transcript_segments.length > 0 && (
        <div className="event-transcript">
          {event.transcript_segments.map((segment) => (
            <p key={segment.id}>
              {segment.content}
              <small>
                {" "}
                [{segment.language.toUpperCase()}]
              </small>
            </p>
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
