import { FormEvent, useMemo, useState } from "react";

import { TimelineCard } from "./components/TimelineCard";
import { api, TimelineEvent, Story } from "./api";

export function App() {
  const [email, setEmail] = useState("gm@example.com");
  const [password, setPassword] = useState("SuperSecret123");
  const [token, setToken] = useState<string | null>(null);
  const [stories, setStories] = useState<Story[]>([]);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [newStoryTitle, setNewStoryTitle] = useState("New Adventure");
  const [error, setError] = useState<string | null>(null);

  const selectedStory = useMemo(
    () => stories.find((story) => story.id === selectedStoryId) ?? null,
    [stories, selectedStoryId]
  );

  async function onRegister(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      const response = await api.register(email, password);
      setToken(response.access_token);
      const loadedStories = await api.listStories(response.access_token);
      setStories(loadedStories);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onCreateStory(e: FormEvent) {
    e.preventDefault();
    if (!token) return;

    try {
      const created = await api.createStory(token, newStoryTitle);
      const nextStories = [created, ...stories];
      setStories(nextStories);
      setSelectedStoryId(created.id);
      setEvents([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function loadEvents(storyId: string) {
    if (!token) return;
    setSelectedStoryId(storyId);
    try {
      const loaded = await api.listEvents(token, storyId);
      setEvents(loaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  return (
    <main className="app-shell">
      <section className="panel auth-panel">
        <h1>DragonWeaver MVP</h1>
        <p>Auth + story portfolio + timeline read model</p>

        {!token ? (
          <form onSubmit={onRegister} className="stack">
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
            />
            <button type="submit">Register and Enter</button>
          </form>
        ) : (
          <p className="token-ok">Authenticated</p>
        )}
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
              <button onClick={() => loadEvents(story.id)}>{story.title}</button>
            </li>
          ))}
        </ul>
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
