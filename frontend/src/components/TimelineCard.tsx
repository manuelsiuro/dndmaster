import type { TimelineEvent } from "../api";

type Props = {
  event: TimelineEvent;
  replayFocused?: boolean;
  onReplayTurn?: (turnId: string) => void;
  activeAudioEventId?: string | null;
};

function formatTurnLabel(turnId: string): string {
  if (turnId.length <= 16) {
    return turnId;
  }
  return `${turnId.slice(0, 8)}...${turnId.slice(-6)}`;
}

function eventTypeIcon(eventType: string): JSX.Element {
  const strokeProps = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const
  };

  if (eventType === "gm_prompt") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path {...strokeProps} d="M4 13h3l4 4V7l-4 4H4z" />
        <path {...strokeProps} d="M15 10a4 4 0 0 1 0 4M17.5 8a7 7 0 0 1 0 8" />
      </svg>
    );
  }
  if (eventType === "player_action") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path {...strokeProps} d="M8 12l3 3 5-6" />
        <circle {...strokeProps} cx="12" cy="12" r="8.5" />
      </svg>
    );
  }
  if (eventType === "choice_prompt" || eventType === "choice_selection") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path {...strokeProps} d="M6 6h12M6 12h12M6 18h12" />
      </svg>
    );
  }
  if (eventType === "outcome") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path {...strokeProps} d="M6 12l4 4 8-8" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle {...strokeProps} cx="12" cy="12" r="8" />
      <path {...strokeProps} d="M12 8v4M12 16h.01" />
    </svg>
  );
}

export function TimelineCard({
  event,
  replayFocused = false,
  onReplayTurn,
  activeAudioEventId = null
}: Props) {
  const isActiveAudio = activeAudioEventId === event.id;

  return (
    <article
      className={`timeline-card event-${event.event_type}${replayFocused ? " timeline-card-focus" : ""}${
        isActiveAudio ? " timeline-card-playing" : ""
      }`}
    >
      <header>
        <span className="event-type">
          <span className="event-type-icon">{eventTypeIcon(event.event_type)}</span>
          <span>{event.event_type.replace("_", " ")}</span>
        </span>
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
          <small>
            {Math.round(event.recording.duration_ms / 1000)}s • {event.recording.codec}
            {isActiveAudio ? " • playing in turn queue" : ""}
          </small>
        </div>
      )}
    </article>
  );
}
