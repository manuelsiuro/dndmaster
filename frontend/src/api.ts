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
  owner_user_id: string;
  title: string;
  description: string | null;
  status: string;
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

export type OrchestrationContext = {
  story_id: string;
  query_text: string;
  language: string;
  assembled_at: string;
  prompt_context: string;
  retrieval_audit_id: string;
  retrieved_memory: Array<{
    id: string;
    memory_type: string;
    content: string;
    similarity: number;
    source_event_id: string | null;
    metadata_json: Record<string, string | number | boolean | null>;
    created_at: string;
  }>;
  summaries: Array<{
    id: string;
    summary_window: string;
    summary_text: string;
    quality_score: number | null;
    created_at: string;
  }>;
  recent_events: Array<{
    id: string;
    event_type: string;
    text_content: string | null;
    language: string | null;
    created_at: string;
  }>;
};

export type OrchestrationRespondPayload = {
  story_id: string;
  player_input: string;
  language?: string | null;
  memory_limit?: number;
  summary_limit?: number;
  timeline_limit?: number;
  persist_to_timeline?: boolean;
};

export type OrchestrationRespondResult = {
  story_id: string;
  provider: string;
  model: string;
  language: string;
  response_text: string;
  timeline_event_id: string | null;
  context: OrchestrationContext;
};

export type TimelineEventType =
  | "gm_prompt"
  | "player_action"
  | "choice_prompt"
  | "choice_selection"
  | "outcome"
  | "system";

export type TimelineEventCreatePayload = {
  story_id: string;
  event_type: TimelineEventType;
  text_content?: string | null;
  language?: string;
  source_event_id?: string | null;
  metadata_json?: Record<string, string | number | boolean | null>;
  audio?: {
    audio_ref: string;
    duration_ms: number;
    codec?: string;
  };
  transcript_segments?: Array<{
    content: string;
    language?: string;
    confidence?: number | null;
    timestamp?: string | null;
  }>;
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

export type AudioUploadResponse = {
  audio_ref: string;
  bytes_size: number;
  content_type: string;
};

export type LlmProvider = "codex" | "claude" | "ollama";
export type AppLanguage = "en" | "fr";
export type VoiceMode = "webrtc_with_fallback";

export type UserSettings = {
  id: string;
  user_id: string;
  llm_provider: LlmProvider;
  llm_model: string | null;
  language: AppLanguage;
  voice_mode: VoiceMode;
  updated_at: string;
};

export type UserSettingsUpdatePayload = Partial<{
  llm_provider: LlmProvider;
  llm_model: string | null;
  language: AppLanguage;
  voice_mode: VoiceMode;
}>;

export type OllamaModelsResponse = {
  available: boolean;
  models: string[];
};

export type StorySave = {
  id: string;
  story_id: string;
  created_by_user_id: string | null;
  label: string;
  created_at: string;
  timeline_event_count: number;
  session_count: number;
};

export type StorySaveSnapshot = {
  version: number;
  saved_at: string;
  story: {
    title: string;
    description: string | null;
    status: string;
  };
  timeline_events: Array<{
    event_type: string;
    text_content: string | null;
    language: string;
    transcript_segments: Array<{
      content: string;
      language: string;
    }>;
  }>;
  sessions: Array<{
    status: string;
    max_players: number;
    players: Array<{
      email: string;
      role: string;
    }>;
  }>;
};

export type StorySaveDetail = StorySave & {
  snapshot_json: StorySaveSnapshot;
};

export type StorySaveRestoreResponse = {
  story: Story;
  timeline_events_restored: number;
};

export type ProgressionEntry = {
  id: string;
  user_id: string;
  story_id: string | null;
  awarded_by_user_id: string | null;
  xp_delta: number;
  reason: string | null;
  created_at: string;
};

export type MyProgression = {
  id: string;
  user_id: string;
  xp_total: number;
  level: number;
  updated_at: string;
  recent_entries: ProgressionEntry[];
};

export type StoryProgression = {
  user_id: string;
  user_email: string;
  xp_total: number;
  level: number;
  last_award_at: string | null;
};

export type ProgressionAwardResponse = {
  progression: StoryProgression;
  entry: ProgressionEntry;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

function wsApiBase(): string {
  if (API_BASE.startsWith("https://")) {
    return `wss://${API_BASE.slice("https://".length)}`;
  }
  if (API_BASE.startsWith("http://")) {
    return `ws://${API_BASE.slice("http://".length)}`;
  }
  return API_BASE;
}

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
  createSave(token: string, storyId: string, label: string) {
    return jsonFetch<StorySave>("/saves", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ story_id: storyId, label })
    });
  },
  listSaves(token: string, storyId: string) {
    return jsonFetch<StorySave[]>(`/saves?story_id=${encodeURIComponent(storyId)}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  getSave(token: string, saveId: string) {
    return jsonFetch<StorySaveDetail>(`/saves/${encodeURIComponent(saveId)}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  restoreSave(token: string, saveId: string, title?: string) {
    return jsonFetch<StorySaveRestoreResponse>(`/saves/${encodeURIComponent(saveId)}/restore`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(title ? { title } : {})
    });
  },
  getMyProgression(token: string) {
    return jsonFetch<MyProgression>("/progression/me", {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  listStoryProgression(token: string, storyId: string) {
    return jsonFetch<StoryProgression[]>(`/progression/story/${encodeURIComponent(storyId)}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  awardStoryXp(
    token: string,
    payload: {
      story_id: string;
      user_id: string;
      xp_delta: number;
      reason?: string | null;
    }
  ) {
    return jsonFetch<ProgressionAwardResponse>("/progression/award", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  listEvents(token: string, storyId: string) {
    return jsonFetch<TimelineEvent[]>(`/timeline/events?story_id=${storyId}&limit=50&offset=0`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  grantVoiceConsent(token: string, storyId: string) {
    return jsonFetch<{ id: string }>("/timeline/consents", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ story_id: storyId, consent_scope: "session_recording" })
    });
  },
  async uploadTimelineAudio(token: string, storyId: string, blob: Blob, filename = "recording.webm") {
    const formData = new FormData();
    formData.append("story_id", storyId);
    formData.append("file", blob, filename);

    const resp = await fetch(`${API_BASE}/timeline/audio-upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || `Request failed: ${resp.status}`);
    }
    return (await resp.json()) as AudioUploadResponse;
  },
  createTimelineEvent(token: string, payload: TimelineEventCreatePayload) {
    return jsonFetch<TimelineEvent>("/timeline/events", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  respondAsGm(token: string, payload: OrchestrationRespondPayload) {
    return jsonFetch<OrchestrationRespondResult>("/orchestration/respond", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  getSettings(token: string) {
    return jsonFetch<UserSettings>("/settings/me", {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  updateSettings(token: string, payload: UserSettingsUpdatePayload) {
    return jsonFetch<UserSettings>("/settings/me", {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  listOllamaModels(token: string) {
    return jsonFetch<OllamaModelsResponse>("/settings/ollama/models", {
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
  voiceStreamUrl(sessionId: string, token: string) {
    return `${wsApiBase()}/sessions/${encodeURIComponent(
      sessionId
    )}/voice/stream?access_token=${encodeURIComponent(token)}`;
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
