import { FormEvent, useEffect, useMemo, useState } from "react";

import { GameSession, SessionStartResponse, api, Story, TimelineEvent } from "./api";
import { TimelineCard } from "./components/TimelineCard";

const DEVICE_KEY = "dw_device_fingerprint";

function getOrCreateDeviceFingerprint() {
  const existing = window.localStorage.getItem(DEVICE_KEY);
  if (existing) return existing;

  const randomPart = window.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
  const created = `device-${randomPart}`;
  window.localStorage.setItem(DEVICE_KEY, created);
  return created;
}

function upsertSession(previous: GameSession[], next: GameSession): GameSession[] {
  return [next, ...previous.filter((item) => item.id !== next.id)];
}

function activePlayerCount(session: GameSession): number {
  return session.players.filter((item) => item.role === "player").length;
}

type AuthMode = "register" | "login";

export function App() {
  const initialJoinToken = useMemo(
    () => new URLSearchParams(window.location.search).get("joinToken") ?? "",
    []
  );

  const [email, setEmail] = useState("gm@example.com");
  const [password, setPassword] = useState("SuperSecret123");
  const [authMode, setAuthMode] = useState<AuthMode>("register");
  const [token, setToken] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [stories, setStories] = useState<Story[]>([]);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [sessions, setSessions] = useState<GameSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [newStoryTitle, setNewStoryTitle] = useState("New Adventure");
  const [maxPlayers, setMaxPlayers] = useState(4);
  const [joinTokenInput, setJoinTokenInput] = useState(initialJoinToken);
  const [deviceFingerprint, setDeviceFingerprint] = useState(getOrCreateDeviceFingerprint);
  const [joinBundle, setJoinBundle] = useState<SessionStartResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedStory = useMemo(
    () => stories.find((story) => story.id === selectedStoryId) ?? null,
    [stories, selectedStoryId]
  );

  const selectedSession = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId]
  );

  const isSelectedSessionHost =
    selectedSession !== null &&
    currentUserId !== null &&
    selectedSession.host_user_id === currentUserId;

  useEffect(() => {
    if (!token || !selectedSessionId) return;

    const streamSessionId = selectedSessionId;
    return api.streamSession(token, streamSessionId, {
      onEvent: ({ session }) => {
        setSessions((previous) => upsertSession(previous, session));
        setJoinBundle((previous) => {
          if (!previous || previous.session.id !== session.id) {
            return previous;
          }
          if (session.status !== "active") {
            return null;
          }
          return { ...previous, session };
        });
      },
      onAccessRevoked: () => {
        setSessions((previous) => previous.filter((item) => item.id !== streamSessionId));
        setSelectedSessionId((previous) => (previous === streamSessionId ? null : previous));
        setJoinBundle((previous) =>
          previous && previous.session.id === streamSessionId ? null : previous
        );
        setError("Session access revoked or no longer available.");
      }
    });
  }, [token, selectedSessionId]);

  async function loadStoryEvents(storyId: string, authToken: string) {
    const loaded = await api.listEvents(authToken, storyId);
    setEvents(loaded);
  }

  async function loadStorySessions(storyId: string, authToken: string) {
    const loaded = await api.listSessions(authToken, storyId);
    setSessions(loaded);
    if (selectedSessionId && !loaded.find((item) => item.id === selectedSessionId)) {
      setSelectedSessionId(null);
      setJoinBundle(null);
    }
  }

  async function onAuthenticate(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      const response =
        authMode === "register" ? await api.register(email, password) : await api.login(email, password);
      setToken(response.access_token);
      setCurrentUserId(response.user.id);

      const [loadedStories, loadedSessions] = await Promise.all([
        api.listStories(response.access_token),
        api.listSessions(response.access_token)
      ]);
      setStories(loadedStories);
      setSessions(loadedSessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onCreateStory(e: FormEvent) {
    e.preventDefault();
    if (!token) return;

    try {
      setError(null);
      const created = await api.createStory(token, newStoryTitle);
      setStories((previous) => [created, ...previous]);
      setSelectedStoryId(created.id);
      setEvents([]);
      setSessions([]);
      setSelectedSessionId(null);
      setJoinBundle(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onSelectStory(storyId: string) {
    if (!token) return;
    setSelectedStoryId(storyId);
    setJoinBundle(null);
    setError(null);
    try {
      await Promise.all([loadStoryEvents(storyId, token), loadStorySessions(storyId, token)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onCreateSession(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStoryId) return;

    try {
      setError(null);
      const created = await api.createSession(token, selectedStoryId, maxPlayers);
      setSessions((previous) => upsertSession(previous, created));
      setSelectedSessionId(created.id);
      setJoinBundle(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onRefreshSession(sessionId: string) {
    if (!token) return;
    try {
      setError(null);
      const refreshed = await api.getSession(token, sessionId);
      setSessions((previous) => upsertSession(previous, refreshed));
      setSelectedSessionId(refreshed.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onStartSession(sessionId: string) {
    if (!token) return;
    try {
      setError(null);
      const started = await api.startSession(token, sessionId, 15);
      setJoinBundle(started);
      setJoinTokenInput(started.join_token);
      setSessions((previous) => upsertSession(previous, started.session));
      setSelectedSessionId(started.session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onRotateJoinToken(sessionId: string) {
    if (!token) return;
    try {
      setError(null);
      const rotated = await api.rotateJoinToken(token, sessionId, 15);
      setJoinBundle(rotated);
      setJoinTokenInput(rotated.join_token);
      setSessions((previous) => upsertSession(previous, rotated.session));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onJoinSession(e: FormEvent) {
    e.preventDefault();
    if (!token || !joinTokenInput.trim() || !deviceFingerprint.trim()) return;

    try {
      setError(null);
      const joined = await api.joinSession(token, joinTokenInput.trim(), deviceFingerprint.trim());
      setSessions((previous) => upsertSession(previous, joined));
      setSelectedSessionId(joined.id);
      setSelectedStoryId(joined.story_id);
      try {
        await loadStoryEvents(joined.story_id, token);
      } catch (err) {
        const message = err instanceof Error ? err.message : "";
        if (message.includes("Story not found")) {
          setEvents([]);
        } else {
          throw err;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onKickPlayer(userId: string) {
    if (!token || !selectedSession) return;
    try {
      setError(null);
      const updated = await api.kickPlayer(token, selectedSession.id, userId);
      setSessions((previous) => upsertSession(previous, updated));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onEndSession() {
    if (!token || !selectedSession) return;
    try {
      setError(null);
      const updated = await api.endSession(token, selectedSession.id);
      setSessions((previous) => upsertSession(previous, updated));
      setJoinBundle(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  return (
    <main className="app-shell">
      <section className="panel auth-panel">
        <h1>DragonWeaver MVP</h1>
        <p>TV host + mobile join by QR token</p>

        {!token ? (
          <form onSubmit={onAuthenticate} className="stack">
            <div className="inline auth-mode-switch">
              <button
                type="button"
                className={authMode === "register" ? "auth-mode-active" : ""}
                onClick={() => setAuthMode("register")}
              >
                Register
              </button>
              <button
                type="button"
                className={authMode === "login" ? "auth-mode-active" : ""}
                onClick={() => setAuthMode("login")}
              >
                Login
              </button>
            </div>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
            />
            <button type="submit">
              {authMode === "register" ? "Register and Enter" : "Login and Enter"}
            </button>
          </form>
        ) : (
          <p className="token-ok">Authenticated</p>
        )}

        <div className="join-panel">
          <h3>Mobile Join</h3>
          <form onSubmit={onJoinSession} className="stack">
            <input
              value={joinTokenInput}
              onChange={(e) => setJoinTokenInput(e.target.value)}
              placeholder="Join token"
              disabled={!token}
            />
            <input
              value={deviceFingerprint}
              onChange={(e) => {
                setDeviceFingerprint(e.target.value);
                window.localStorage.setItem(DEVICE_KEY, e.target.value);
              }}
              placeholder="Device fingerprint"
              disabled={!token}
            />
            <button type="submit" disabled={!token}>
              Join Session
            </button>
          </form>
        </div>

        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel stories-panel">
        <h2>Stories</h2>
        <form onSubmit={onCreateStory} className="stack inline">
          <input
            value={newStoryTitle}
            onChange={(e) => setNewStoryTitle(e.target.value)}
            placeholder="Story title"
          />
          <button type="submit" disabled={!token}>
            Create
          </button>
        </form>
        <ul>
          {stories.map((story) => (
            <li key={story.id}>
              <button onClick={() => onSelectStory(story.id)} disabled={!token}>
                {story.title}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel session-panel">
        <h2>Sessions {selectedStory ? `- ${selectedStory.title}` : ""}</h2>
        {!selectedStoryId ? (
          <p>Select a story first to manage session lobby.</p>
        ) : (
          <>
            <form onSubmit={onCreateSession} className="stack inline session-create">
              <input
                type="number"
                min={1}
                max={4}
                value={maxPlayers}
                onChange={(e) => setMaxPlayers(Number(e.target.value))}
              />
              <button type="submit" disabled={!token}>
                New Session
              </button>
            </form>

            <ul className="session-list">
              {sessions.map((session) => (
                <li key={session.id}>
                  <button
                    className={selectedSessionId === session.id ? "active-session" : ""}
                    onClick={() => {
                      setSelectedSessionId(session.id);
                      setJoinBundle(null);
                    }}
                  >
                    {session.status.toUpperCase()} • {activePlayerCount(session)}/{session.max_players} players
                  </button>
                </li>
              ))}
            </ul>

            {selectedSession && (
              <div className="session-details stack">
                <div className="inline session-actions">
                  <button onClick={() => onRefreshSession(selectedSession.id)} disabled={!token}>
                    Refresh
                  </button>
                  {isSelectedSessionHost && selectedSession.status === "lobby" && (
                    <button onClick={() => onStartSession(selectedSession.id)} disabled={!token}>
                      Start + Generate QR Token
                    </button>
                  )}
                  {isSelectedSessionHost && selectedSession.status === "active" && (
                    <button onClick={() => onRotateJoinToken(selectedSession.id)} disabled={!token}>
                      Rotate Join Token
                    </button>
                  )}
                  {isSelectedSessionHost && selectedSession.status !== "ended" && (
                    <button onClick={onEndSession} disabled={!token}>
                      End Session
                    </button>
                  )}
                </div>

                <ul className="session-players">
                  {selectedSession.players.map((player) => (
                    <li key={player.user_id}>
                      <span>
                        {player.user_email} ({player.role})
                      </span>
                      {isSelectedSessionHost && player.role !== "host" && (
                        <button onClick={() => onKickPlayer(player.user_id)}>Kick</button>
                      )}
                    </li>
                  ))}
                </ul>

                {joinBundle && selectedSession.status === "active" && (
                  <div className="qr-block">
                    <p>
                      Join token expires at:{" "}
                      <strong>{new Date(joinBundle.expires_at).toLocaleTimeString()}</strong>
                    </p>
                    <code className="join-token">{joinBundle.join_token}</code>
                    <a href={joinBundle.join_url} target="_blank" rel="noreferrer">
                      {joinBundle.join_url}
                    </a>
                    <img
                      className="qr-image"
                      alt="Join session QR code"
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(
                        joinBundle.join_url
                      )}`}
                    />
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </section>

      <section className="panel timeline-panel">
        <h2>Timeline {selectedStory ? `- ${selectedStory.title}` : ""}</h2>
        {selectedStoryId ? (
          events.length > 0 ? (
            <div className="timeline-grid">
              {events.map((event) => (
                <TimelineCard key={event.id} event={event} />
              ))}
            </div>
          ) : (
            <p>No events yet for this story.</p>
          )
        ) : (
          <p>Select a story to load timeline events.</p>
        )}
      </section>
    </main>
  );
}
