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

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Request failed: ${resp.status}`);
  }

  return resp.json() as Promise<T>;
}

export const api = {
  register(email: string, password: string) {
    return jsonFetch<RegisterResponse>("/auth/register", {
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
  }
};
