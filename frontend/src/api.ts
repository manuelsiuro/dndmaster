export type RegisterResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
  };
};

export type Story = {
  id: string;
  title: string;
  description: string | null;
  created_at: string;
};

export type TimelineEvent = {
  id: string;
  event_type: string;
  actor_id: string | null;
  text_content: string | null;
  created_at: string;
  transcript_segments: Array<{ id: string; content: string }>;
  recording: { id: string; audio_ref: string; duration_ms: number } | null;
};

export type SessionRole = "host" | "player";
export type SessionStatus = "lobby" | "active" | "ended";

export type SessionPlayer = {
  user_id: string;
  user_email: string;
  role: SessionRole;
  joined_at: string;
};

export type GameSession = {
  id: string;
  story_id: string;
  host_user_id: string;
  status: SessionStatus;
  max_players: number;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  active_join_token_expires_at: string | null;
  players: SessionPlayer[];
};

export type SessionStartResponse = {
  session: GameSession;
  join_token: string;
  join_url: string;
  expires_at: string;
};

export type SessionRealtimeEvent = {
  change_type: string;
  session: GameSession;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Request failed: ${resp.status}`);
  }

  return resp.json() as Promise<T>;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export const api = {
  register(email: string, password: string) {
    return jsonFetch<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  },
  login(email: string, password: string) {
    return jsonFetch<RegisterResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  },
  createStory(token: string, title: string) {
    return jsonFetch<Story>("/stories", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ title })
    });
  },
  listStories(token: string) {
    return jsonFetch<Story[]>("/stories", {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  listEvents(token: string, storyId: string) {
    return jsonFetch<TimelineEvent[]>(`/timeline/events?story_id=${storyId}&limit=50&offset=0`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  createSession(token: string, storyId: string, maxPlayers = 4) {
    return jsonFetch<GameSession>("/sessions", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ story_id: storyId, max_players: maxPlayers })
    });
  },
  listSessions(token: string, storyId?: string) {
    const query = storyId ? `?story_id=${encodeURIComponent(storyId)}` : "";
    return jsonFetch<GameSession[]>(`/sessions${query}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  getSession(token: string, sessionId: string) {
    return jsonFetch<GameSession>(`/sessions/${sessionId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  startSession(token: string, sessionId: string, tokenTtlMinutes = 15) {
    return jsonFetch<SessionStartResponse>(`/sessions/${sessionId}/start`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ token_ttl_minutes: tokenTtlMinutes })
    });
  },
  rotateJoinToken(token: string, sessionId: string, tokenTtlMinutes = 15) {
    return jsonFetch<SessionStartResponse>(`/sessions/${sessionId}/join-token`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ token_ttl_minutes: tokenTtlMinutes })
    });
  },
  joinSession(token: string, joinToken: string, deviceFingerprint: string) {
    return jsonFetch<GameSession>("/sessions/join", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        join_token: joinToken,
        device_fingerprint: deviceFingerprint
      })
    });
  },
  kickPlayer(token: string, sessionId: string, userId: string) {
    return jsonFetch<GameSession>(`/sessions/${sessionId}/kick`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ user_id: userId })
    });
  },
  endSession(token: string, sessionId: string) {
    return jsonFetch<GameSession>(`/sessions/${sessionId}/end`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  streamSession(
    token: string,
    sessionId: string,
    handlers: {
      onEvent: (event: SessionRealtimeEvent) => void;
      onAccessRevoked?: () => void;
      onError?: (message: string) => void;
    }
  ) {
    const controller = new AbortController();
    const url = `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/stream`;
    const decoder = new TextDecoder();

    const parseBlock = (block: string) => {
      const lines = block.split("\n");
      const dataParts: string[] = [];

      for (const line of lines) {
        if (line.startsWith(":")) {
          continue;
        }
        if (line.startsWith("data:")) {
          dataParts.push(line.slice(5).trimStart());
        }
      }

      if (dataParts.length === 0) return;

      try {
        const parsed = JSON.parse(dataParts.join("\n")) as SessionRealtimeEvent;
        if (parsed?.session?.id) {
          handlers.onEvent(parsed);
        }
      } catch (err) {
        handlers.onError?.(err instanceof Error ? err.message : "Failed to parse realtime event");
      }
    };

    void (async () => {
      while (!controller.signal.aborted) {
        try {
          const resp = await fetch(url, {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: "text/event-stream"
            },
            signal: controller.signal
          });

          if (resp.status === 403 || resp.status === 404) {
            handlers.onAccessRevoked?.();
            return;
          }
          if (!resp.ok) {
            throw new Error(`Stream request failed: ${resp.status}`);
          }
          if (!resp.body) {
            throw new Error("Stream response body is empty");
          }

          const reader = resp.body.getReader();
          let buffer = "";

          while (!controller.signal.aborted) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            while (true) {
              const boundary = buffer.indexOf("\n\n");
              if (boundary < 0) break;
              const block = buffer.slice(0, boundary);
              buffer = buffer.slice(boundary + 2);
              parseBlock(block);
            }
          }
        } catch (err) {
          if (controller.signal.aborted) {
            return;
          }
          handlers.onError?.(err instanceof Error ? err.message : "Realtime stream disconnected");
          await sleep(1000);
        }
      }
    })();

    return () => {
      controller.abort();
    };
  }
};
