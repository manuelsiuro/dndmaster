import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  AppLanguage,
  GameSession,
  LlmProvider,
  OrchestrationRespondResult,
  MyProgression,
  ProgressionEntry,
  ProgressionAwardResponse,
  SessionStartResponse,
  StoryProgression,
  StorySave,
  StorySaveDetail,
  TimelineEventType,
  UserSettings,
  api,
  Story,
  TimelineEvent
} from "./api";
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
type VoicePeerState = "idle" | "connecting" | "connected" | "disconnected";

type VoicePeer = {
  user_id: string;
  user_email: string;
  role: "host" | "player";
  muted: boolean;
  state: VoicePeerState;
};

type VoiceSignalMessage = {
  type: "signal";
  from_user_id: string;
  signal_type: "offer" | "answer" | "ice";
  payload: unknown;
};

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
  const [saves, setSaves] = useState<StorySave[]>([]);
  const [selectedSaveId, setSelectedSaveId] = useState<string | null>(null);
  const [selectedSaveDetail, setSelectedSaveDetail] = useState<StorySaveDetail | null>(null);
  const [saveLabel, setSaveLabel] = useState("Checkpoint");
  const [restoreTitle, setRestoreTitle] = useState("");
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [isLoadingSaves, setIsLoadingSaves] = useState(false);
  const [isCreatingSave, setIsCreatingSave] = useState(false);
  const [isLoadingSaveDetail, setIsLoadingSaveDetail] = useState(false);
  const [isRestoringSave, setIsRestoringSave] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [newStoryTitle, setNewStoryTitle] = useState("New Adventure");
  const [maxPlayers, setMaxPlayers] = useState(4);
  const [joinTokenInput, setJoinTokenInput] = useState(initialJoinToken);
  const [deviceFingerprint, setDeviceFingerprint] = useState(getOrCreateDeviceFingerprint);
  const [joinBundle, setJoinBundle] = useState<SessionStartResponse | null>(null);
  const [eventType, setEventType] = useState<TimelineEventType>("player_action");
  const [eventText, setEventText] = useState("");
  const [eventTranscript, setEventTranscript] = useState("");
  const [gmPlayerInput, setGmPlayerInput] = useState("");
  const [latestGmResponse, setLatestGmResponse] = useState<OrchestrationRespondResult | null>(null);
  const [eventLanguage, setEventLanguage] = useState("en");
  const [isSubmittingEvent, setIsSubmittingEvent] = useState(false);
  const [isGeneratingGmResponse, setIsGeneratingGmResponse] = useState(false);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [recordingDurationMs, setRecordingDurationMs] = useState<number>(0);
  const [recordingPreviewUrl, setRecordingPreviewUrl] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [consentedStoryIds, setConsentedStoryIds] = useState<string[]>([]);
  const [settingsDraft, setSettingsDraft] = useState<UserSettings | null>(null);
  const [settingsStatus, setSettingsStatus] = useState<string | null>(null);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaAvailable, setOllamaAvailable] = useState(false);
  const [isLoadingOllamaModels, setIsLoadingOllamaModels] = useState(false);
  const [myProgression, setMyProgression] = useState<MyProgression | null>(null);
  const [storyProgressionRows, setStoryProgressionRows] = useState<StoryProgression[]>([]);
  const [xpDraftByUser, setXpDraftByUser] = useState<Record<string, string>>({});
  const [reasonDraftByUser, setReasonDraftByUser] = useState<Record<string, string>>({});
  const [awardingUserId, setAwardingUserId] = useState<string | null>(null);
  const [voiceConnectionState, setVoiceConnectionState] = useState<"disconnected" | "connecting" | "connected">(
    "disconnected"
  );
  const [voiceStatus, setVoiceStatus] = useState<string | null>(null);
  const [voicePeers, setVoicePeers] = useState<VoicePeer[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordingStartedAtRef = useRef<number>(0);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const voiceLocalStreamRef = useRef<MediaStream | null>(null);
  const voiceConnectionsRef = useRef<Map<string, RTCPeerConnection>>(new Map());
  const pendingIceCandidatesRef = useRef<Map<string, RTCIceCandidateInit[]>>(new Map());
  const remoteAudioElsRef = useRef<Map<string, HTMLAudioElement>>(new Map());
  const [error, setError] = useState<string | null>(null);

  const selectedStory = useMemo(
    () => stories.find((story) => story.id === selectedStoryId) ?? null,
    [stories, selectedStoryId]
  );

  const selectedSession = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId]
  );

  const selectedSave = useMemo(
    () => saves.find((save) => save.id === selectedSaveId) ?? null,
    [saves, selectedSaveId]
  );

  const isSelectedSessionHost =
    selectedSession !== null &&
    currentUserId !== null &&
    selectedSession.host_user_id === currentUserId;

  const isSelectedSessionPlayer =
    selectedSession !== null &&
    currentUserId !== null &&
    selectedSession.host_user_id !== currentUserId;

  const canManageSelectedStory = Boolean(token && selectedStoryId) && !isSelectedSessionPlayer;
  const canComposeTimeline =
    Boolean(token && selectedStoryId) && (selectedSession === null || isSelectedSessionHost);

  function upsertVoicePeer(peer: Omit<VoicePeer, "state">, state: VoicePeerState = "idle") {
    setVoicePeers((previous) => {
      const existing = previous.find((item) => item.user_id === peer.user_id);
      const nextItem = existing
        ? {
            ...existing,
            ...peer,
            state: existing.state === "connected" ? "connected" : state
          }
        : { ...peer, state };
      return [nextItem, ...previous.filter((item) => item.user_id !== peer.user_id)];
    });
  }

  function markVoicePeerState(userId: string, nextState: VoicePeerState) {
    setVoicePeers((previous) =>
      previous.map((item) => (item.user_id === userId ? { ...item, state: nextState } : item))
    );
  }

  function setVoicePeerMuted(userId: string, muted: boolean) {
    setVoicePeers((previous) =>
      previous.map((item) => (item.user_id === userId ? { ...item, muted } : item))
    );
  }

  function removeVoicePeer(userId: string) {
    setVoicePeers((previous) => previous.filter((item) => item.user_id !== userId));
  }

  function closeVoicePeerConnection(peerUserId: string) {
    const connection = voiceConnectionsRef.current.get(peerUserId);
    if (connection) {
      connection.onicecandidate = null;
      connection.ontrack = null;
      connection.onconnectionstatechange = null;
      connection.close();
      voiceConnectionsRef.current.delete(peerUserId);
    }

    const audio = remoteAudioElsRef.current.get(peerUserId);
    if (audio) {
      audio.pause();
      audio.srcObject = null;
      remoteAudioElsRef.current.delete(peerUserId);
    }
    pendingIceCandidatesRef.current.delete(peerUserId);
  }

  function teardownVoiceConnection(announce = true) {
    const socket = voiceSocketRef.current;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
      voiceSocketRef.current = null;
    }

    for (const peerUserId of voiceConnectionsRef.current.keys()) {
      closeVoicePeerConnection(peerUserId);
    }
    voiceConnectionsRef.current.clear();
    pendingIceCandidatesRef.current.clear();

    const localStream = voiceLocalStreamRef.current;
    if (localStream) {
      localStream.getTracks().forEach((track) => track.stop());
      voiceLocalStreamRef.current = null;
    }

    setVoicePeers([]);
    setVoiceConnectionState("disconnected");
    if (announce) {
      setVoiceStatus("Voice disconnected. Fallback recording remains available.");
    }
  }

  useEffect(() => {
    return () => {
      if (recordingPreviewUrl) {
        URL.revokeObjectURL(recordingPreviewUrl);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      teardownVoiceConnection(false);
    };
  }, [recordingPreviewUrl]);

  useEffect(() => {
    return () => {
      teardownVoiceConnection(false);
    };
  }, [selectedSessionId, token]);

  useEffect(() => {
    if (selectedSession?.status !== "active" && voiceConnectionState !== "disconnected") {
      teardownVoiceConnection(false);
      setVoiceStatus("Voice closed because the session is no longer active.");
    }
  }, [selectedSession?.status, voiceConnectionState]);

  useEffect(() => {
    if (!token || !selectedSessionId) return;

    const streamSessionId = selectedSessionId;
    return api.streamSession(token, streamSessionId, {
      onEvent: ({ session }) => {
        setSessions((previous) => upsertSession(previous, session));
        void refreshProgressionState(session.story_id, token).catch(() => {
          // Best-effort sync to keep progression widgets current during live lobby updates.
        });
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

  function clearRecording() {
    if (recordingPreviewUrl) {
      URL.revokeObjectURL(recordingPreviewUrl);
    }
    setRecordingBlob(null);
    setRecordingDurationMs(0);
    setRecordingPreviewUrl(null);
  }

  async function loadStoryEvents(storyId: string, authToken: string) {
    const loaded = await api.listEvents(authToken, storyId);
    setEvents(loaded);
  }

  async function loadSettings(authToken: string) {
    const [settings, models] = await Promise.all([
      api.getSettings(authToken),
      api.listOllamaModels(authToken)
    ]);
    setSettingsDraft(settings);
    setOllamaModels(models.models);
    setOllamaAvailable(models.available);
  }

  async function loadStorySessions(storyId: string, authToken: string) {
    const loaded = await api.listSessions(authToken, storyId);
    setSessions(loaded);
    if (selectedSessionId && !loaded.find((item) => item.id === selectedSessionId)) {
      setSelectedSessionId(null);
      setJoinBundle(null);
    }
  }

  async function loadStorySaves(storyId: string, authToken: string) {
    try {
      setIsLoadingSaves(true);
      const loaded = await api.listSaves(authToken, storyId);
      setSaves(loaded);
      setSelectedSaveId((previous) =>
        previous && loaded.some((item) => item.id === previous) ? previous : null
      );
      setSelectedSaveDetail((previous) =>
        previous && loaded.some((item) => item.id === previous.id) ? previous : null
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (message.includes("Story not found")) {
        setSaves([]);
        setSelectedSaveId(null);
        setSelectedSaveDetail(null);
        return;
      }
      throw err;
    } finally {
      setIsLoadingSaves(false);
    }
  }

  async function loadMyProgression(authToken: string) {
    const progression = await api.getMyProgression(authToken);
    setMyProgression(progression);
  }

  async function loadStoryProgression(storyId: string, authToken: string) {
    try {
      const rows = await api.listStoryProgression(authToken, storyId);
      setStoryProgressionRows(rows);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (message.includes("Story not found")) {
        setStoryProgressionRows([]);
        return;
      }
      throw err;
    }
  }

  async function refreshProgressionState(storyId: string, authToken: string) {
    await Promise.all([loadStoryProgression(storyId, authToken), loadMyProgression(authToken)]);
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
      await loadMyProgression(response.access_token);
      setSaves([]);
      setSelectedSaveId(null);
      setSelectedSaveDetail(null);
      setRestoreTitle("");
      setSaveStatus(null);
      await loadSettings(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onRefreshOllamaModels() {
    if (!token) return;
    try {
      setError(null);
      setIsLoadingOllamaModels(true);
      const models = await api.listOllamaModels(token);
      setOllamaModels(models.models);
      setOllamaAvailable(models.available);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsLoadingOllamaModels(false);
    }
  }

  async function onSaveSettings(e: FormEvent) {
    e.preventDefault();
    if (!token || !settingsDraft) return;
    try {
      setIsSavingSettings(true);
      setError(null);
      const updated = await api.updateSettings(token, {
        llm_provider: settingsDraft.llm_provider,
        llm_model: settingsDraft.llm_model,
        language: settingsDraft.language,
        voice_mode: settingsDraft.voice_mode
      });
      setSettingsDraft(updated);
      setSettingsStatus(`Saved at ${new Date(updated.updated_at).toLocaleTimeString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsSavingSettings(false);
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
      setSaves([]);
      setStoryProgressionRows([]);
      setSelectedSaveId(null);
      setSelectedSaveDetail(null);
      setRestoreTitle("");
      setSaveStatus(null);
      setSelectedSessionId(null);
      setJoinBundle(null);
      setGmPlayerInput("");
      setLatestGmResponse(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onSelectStory(storyId: string) {
    if (!token) return;
    setSelectedStoryId(storyId);
    setJoinBundle(null);
    setSelectedSaveId(null);
    setSelectedSaveDetail(null);
    setRestoreTitle("");
    setSaveStatus(null);
    setStoryProgressionRows([]);
    setGmPlayerInput("");
    setLatestGmResponse(null);
    setError(null);
    try {
      await Promise.all([
        loadStoryEvents(storyId, token),
        loadStorySessions(storyId, token),
        loadStorySaves(storyId, token),
        loadStoryProgression(storyId, token)
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onRefreshStorySaves() {
    if (!token || !selectedStoryId) return;
    try {
      setError(null);
      await loadStorySaves(selectedStoryId, token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onCreateSave(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStoryId) return;

    const nextLabel = saveLabel.trim() || "Checkpoint";

    try {
      setIsCreatingSave(true);
      setError(null);
      setSaveStatus(null);
      const created = await api.createSave(token, selectedStoryId, nextLabel);
      setSaves((previous) => [created, ...previous.filter((item) => item.id !== created.id)]);
      setSelectedSaveId(created.id);
      setSaveLabel("Checkpoint");

      const detail = await api.getSave(token, created.id);
      setSelectedSaveDetail(detail);
      setRestoreTitle(`${detail.snapshot_json.story.title} (Restored)`);
      setSaveStatus(`Saved "${created.label}" at ${new Date(created.created_at).toLocaleTimeString()}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsCreatingSave(false);
    }
  }

  async function onSelectSave(saveId: string) {
    if (!token) return;
    try {
      setIsLoadingSaveDetail(true);
      setError(null);
      setSelectedSaveId(saveId);
      const detail = await api.getSave(token, saveId);
      setSelectedSaveDetail(detail);
      if (!restoreTitle.trim()) {
        setRestoreTitle(`${detail.snapshot_json.story.title} (Restored)`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsLoadingSaveDetail(false);
    }
  }

  async function onRestoreSave(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedSaveId) return;
    try {
      setIsRestoringSave(true);
      setError(null);
      setSaveStatus(null);
      const nextTitle = restoreTitle.trim();
      const restored = await api.restoreSave(token, selectedSaveId, nextTitle || undefined);

      setStories((previous) => [restored.story, ...previous.filter((story) => story.id !== restored.story.id)]);
      setSelectedStoryId(restored.story.id);
      setSelectedSessionId(null);
      setJoinBundle(null);
      setSelectedSaveId(null);
      setSelectedSaveDetail(null);
      setRestoreTitle("");
      setSaveStatus(
        `Restored ${restored.timeline_events_restored} events into "${restored.story.title}".`
      );
      setGmPlayerInput("");
      setLatestGmResponse(null);

      await Promise.all([
        loadStoryEvents(restored.story.id, token),
        loadStorySessions(restored.story.id, token),
        loadStorySaves(restored.story.id, token),
        loadStoryProgression(restored.story.id, token)
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsRestoringSave(false);
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
      await refreshProgressionState(refreshed.story_id, token);
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
      await refreshProgressionState(started.session.story_id, token);
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
      setSaves([]);
      setSelectedSaveId(null);
      setSelectedSaveDetail(null);
      setRestoreTitle("");
      setSaveStatus(null);
      setStoryProgressionRows([]);
      setGmPlayerInput("");
      setLatestGmResponse(null);
      await Promise.all([
        (async () => {
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
        })(),
        loadStorySessions(joined.story_id, token),
        loadStorySaves(joined.story_id, token),
        refreshProgressionState(joined.story_id, token)
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  async function onAwardXp(userId: string) {
    if (!token || !selectedStoryId || !canManageSelectedStory) return;
    const delta = Number(xpDraftByUser[userId] ?? "0");
    if (!Number.isFinite(delta) || delta <= 0) {
      setError("XP award must be a positive number.");
      return;
    }

    try {
      setAwardingUserId(userId);
      setError(null);
      const reason = reasonDraftByUser[userId]?.trim();
      const response: ProgressionAwardResponse = await api.awardStoryXp(token, {
        story_id: selectedStoryId,
        user_id: userId,
        xp_delta: Math.floor(delta),
        reason: reason ? reason : null
      });

      setStoryProgressionRows((previous) =>
        [response.progression, ...previous.filter((item) => item.user_id !== userId)].sort(
          (a, b) => b.xp_total - a.xp_total || a.user_email.localeCompare(b.user_email)
        )
      );

      setXpDraftByUser((previous) => ({ ...previous, [userId]: "" }));
      setReasonDraftByUser((previous) => ({ ...previous, [userId]: "" }));

      setMyProgression((previous) => {
        if (!previous || previous.user_id !== userId) {
          return previous;
        }
        const newEntry: ProgressionEntry = response.entry;
        const xpTotal = response.progression.xp_total;
        return {
          ...previous,
          xp_total: xpTotal,
          level: response.progression.level,
          recent_entries: [newEntry, ...previous.recent_entries].slice(0, 20)
        };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setAwardingUserId(null);
    }
  }

  async function onKickPlayer(userId: string) {
    if (!token || !selectedSession) return;
    try {
      setError(null);
      const updated = await api.kickPlayer(token, selectedSession.id, userId);
      setSessions((previous) => upsertSession(previous, updated));
      await refreshProgressionState(updated.story_id, token);
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

  function sendVoiceSignal(
    targetUserId: string,
    signalType: "offer" | "answer" | "ice",
    payload: unknown
  ) {
    const socket = voiceSocketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    socket.send(
      JSON.stringify({
        type: "signal",
        target_user_id: targetUserId,
        signal_type: signalType,
        payload
      })
    );
  }

  function sendVoiceModeration(
    targetUserId: string,
    action: "mute" | "unmute" | "disconnect"
  ) {
    const socket = voiceSocketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    socket.send(
      JSON.stringify({
        type: "moderation",
        target_user_id: targetUserId,
        action
      })
    );
  }

  function queuePendingIceCandidate(peerUserId: string, candidate: RTCIceCandidateInit) {
    const previous = pendingIceCandidatesRef.current.get(peerUserId) ?? [];
    pendingIceCandidatesRef.current.set(peerUserId, [...previous, candidate]);
  }

  async function flushPendingIceCandidates(peerUserId: string, connection: RTCPeerConnection) {
    const pending = pendingIceCandidatesRef.current.get(peerUserId) ?? [];
    if (pending.length === 0) {
      return;
    }
    pendingIceCandidatesRef.current.delete(peerUserId);
    for (const candidate of pending) {
      try {
        await connection.addIceCandidate(candidate);
      } catch {
        // Best-effort candidate replay for out-of-order signaling.
      }
    }
  }

  async function ensurePeerConnection(peerUserId: string, initiateOffer: boolean) {
    let connection = voiceConnectionsRef.current.get(peerUserId);
    if (connection) {
      return connection;
    }

    const localStream = voiceLocalStreamRef.current;
    if (!localStream) {
      return null;
    }

    connection = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
    });
    voiceConnectionsRef.current.set(peerUserId, connection);
    markVoicePeerState(peerUserId, "connecting");

    for (const track of localStream.getTracks()) {
      connection.addTrack(track, localStream);
    }

    connection.onicecandidate = (event) => {
      if (event.candidate) {
        sendVoiceSignal(peerUserId, "ice", event.candidate.toJSON());
      }
    };

    connection.ontrack = (event) => {
      const [stream] = event.streams;
      if (!stream) {
        return;
      }
      let audio = remoteAudioElsRef.current.get(peerUserId);
      if (!audio) {
        audio = new Audio();
        audio.autoplay = true;
        remoteAudioElsRef.current.set(peerUserId, audio);
      }
      audio.srcObject = stream;
      void audio.play().catch(() => {
        setVoiceStatus("Autoplay blocked. Interact with the page to hear remote players.");
      });
    };

    connection.onconnectionstatechange = () => {
      switch (connection?.connectionState) {
        case "connected":
          markVoicePeerState(peerUserId, "connected");
          break;
        case "disconnected":
        case "failed":
        case "closed":
          markVoicePeerState(peerUserId, "disconnected");
          closeVoicePeerConnection(peerUserId);
          break;
        default:
          break;
      }
    };

    if (initiateOffer) {
      try {
        const offer = await connection.createOffer();
        await connection.setLocalDescription(offer);
        sendVoiceSignal(peerUserId, "offer", offer);
      } catch {
        setVoiceStatus("Unable to negotiate live voice. Use fallback recording.");
      }
    }

    return connection;
  }

  async function handleVoiceSignalMessage(message: VoiceSignalMessage) {
    const peerUserId = message.from_user_id;
    upsertVoicePeer(
      {
        user_id: peerUserId,
        user_email: "Connected player",
        role: "player",
        muted: false
      },
      "connecting"
    );

    if (message.signal_type === "ice") {
      if (typeof message.payload !== "object" || message.payload === null) {
        return;
      }
      const candidate = message.payload as RTCIceCandidateInit;
      const connection = voiceConnectionsRef.current.get(peerUserId);
      if (!connection || connection.remoteDescription === null) {
        queuePendingIceCandidate(peerUserId, candidate);
        return;
      }
      try {
        await connection.addIceCandidate(candidate);
      } catch {
        queuePendingIceCandidate(peerUserId, candidate);
      }
      return;
    }

    if (typeof message.payload !== "object" || message.payload === null) {
      return;
    }

    const description = message.payload as RTCSessionDescriptionInit;
    if (message.signal_type === "offer") {
      const connection = await ensurePeerConnection(peerUserId, false);
      if (!connection) {
        return;
      }
      await connection.setRemoteDescription(description);
      await flushPendingIceCandidates(peerUserId, connection);
      const answer = await connection.createAnswer();
      await connection.setLocalDescription(answer);
      sendVoiceSignal(peerUserId, "answer", answer);
      return;
    }

    const existing = voiceConnectionsRef.current.get(peerUserId);
    if (!existing) {
      return;
    }
    await existing.setRemoteDescription(description);
    await flushPendingIceCandidates(peerUserId, existing);
  }

  async function onConnectVoice() {
    if (!token || !selectedSession || selectedSession.status !== "active") {
      return;
    }
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof window.RTCPeerConnection === "undefined" ||
      typeof window.WebSocket === "undefined"
    ) {
      setVoiceStatus("Browser does not support WebRTC voice. Use fallback recording.");
      return;
    }
    if (voiceConnectionState !== "disconnected") {
      return;
    }

    try {
      setError(null);
      setVoiceStatus("Connecting voice...");
      setVoiceConnectionState("connecting");
      const localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      voiceLocalStreamRef.current = localStream;

      const socket = new WebSocket(api.voiceStreamUrl(selectedSession.id, token));
      voiceSocketRef.current = socket;

      socket.onopen = () => {
        setVoiceStatus("Voice signaling connected. Negotiating peers...");
      };

      socket.onmessage = (event) => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(typeof event.data === "string" ? event.data : "{}");
        } catch {
          setVoiceStatus("Received invalid voice signaling message.");
          return;
        }

        if (!parsed || typeof parsed !== "object") {
          return;
        }

        const message = parsed as Record<string, unknown>;
        const messageType = typeof message.type === "string" ? message.type : "";

        if (messageType === "voice_snapshot") {
          const peers = Array.isArray(message.peers) ? message.peers : [];
          const mutedUserIds = Array.isArray(message.muted_user_ids)
            ? message.muted_user_ids.map((item) => String(item))
            : [];
          const normalizedPeers: VoicePeer[] = peers
            .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
            .map((item): VoicePeer => {
              const role: VoicePeer["role"] = item.role === "host" ? "host" : "player";
              return {
                user_id: String(item.user_id ?? ""),
                user_email: String(item.user_email ?? "Connected player"),
                role,
                muted: Boolean(item.muted) || mutedUserIds.includes(String(item.user_id ?? "")),
                state: "connecting"
              };
            })
            .filter((item) => item.user_id.length > 0);

          setVoicePeers(normalizedPeers);
          setVoiceConnectionState("connected");
          setVoiceStatus(
            normalizedPeers.length > 0
              ? `Voice connected with ${normalizedPeers.length} remote peer(s).`
              : "Voice connected. Waiting for peers..."
          );

          if (currentUserId && mutedUserIds.includes(currentUserId)) {
            const localStream = voiceLocalStreamRef.current;
            if (localStream) {
              localStream.getAudioTracks().forEach((track) => {
                track.enabled = false;
              });
            }
            setVoiceStatus("You are muted by the host.");
          }

          for (const peer of normalizedPeers) {
            void ensurePeerConnection(peer.user_id, true);
          }
          return;
        }

        if (messageType === "peer_joined") {
          const peerUserId = String(message.user_id ?? "");
          if (!peerUserId) {
            return;
          }
          upsertVoicePeer(
            {
              user_id: peerUserId,
              user_email: String(message.user_email ?? "Connected player"),
              role: message.role === "host" ? "host" : "player",
              muted: Boolean(message.muted)
            },
            "connecting"
          );
          return;
        }

        if (messageType === "peer_left") {
          const peerUserId = String(message.user_id ?? "");
          if (!peerUserId) {
            return;
          }
          closeVoicePeerConnection(peerUserId);
          removeVoicePeer(peerUserId);
          return;
        }

        if (messageType === "moderation") {
          const action = String(message.action ?? "");
          const targetUserId = String(message.target_user_id ?? "");
          const targetUserEmail = String(message.target_user_email ?? "player");
          if (!targetUserId) {
            return;
          }

          if (action === "mute" || action === "unmute") {
            const muted = action === "mute";
            if (targetUserId === currentUserId) {
              const localStream = voiceLocalStreamRef.current;
              if (localStream) {
                localStream.getAudioTracks().forEach((track) => {
                  track.enabled = !muted;
                });
              }
              setVoiceStatus(muted ? "You were muted by the host." : "Host unmuted your microphone.");
            } else {
              setVoiceStatus(
                muted
                  ? `Host muted ${targetUserEmail}'s microphone.`
                  : `Host unmuted ${targetUserEmail}'s microphone.`
              );
            }
            setVoicePeerMuted(targetUserId, muted);
            return;
          }

          if (action === "disconnect") {
            if (targetUserId === currentUserId) {
              teardownVoiceConnection(false);
              setVoiceStatus("Disconnected by host from live voice. Use fallback recording.");
              return;
            }
            closeVoicePeerConnection(targetUserId);
            removeVoicePeer(targetUserId);
            setVoiceStatus(`Host disconnected ${targetUserEmail} from live voice.`);
            return;
          }
        }

        if (messageType === "signal") {
          const signalType = String(message.signal_type ?? "");
          const fromUserId = String(message.from_user_id ?? "");
          if (!fromUserId || !["offer", "answer", "ice"].includes(signalType)) {
            return;
          }
          void handleVoiceSignalMessage({
            type: "signal",
            from_user_id: fromUserId,
            signal_type: signalType as VoiceSignalMessage["signal_type"],
            payload: message.payload
          });
          return;
        }

        if (messageType === "error") {
          setVoiceStatus(String(message.detail ?? "Voice signaling error"));
        }
      };

      socket.onerror = () => {
        setVoiceStatus("Voice signaling error. Use fallback recording.");
      };

      socket.onclose = () => {
        if (voiceSocketRef.current === socket) {
          teardownVoiceConnection(false);
          setVoiceStatus("Voice disconnected. Use timeline audio fallback.");
        }
      };
    } catch (err) {
      teardownVoiceConnection(false);
      setVoiceConnectionState("disconnected");
      setVoiceStatus("Unable to start microphone. Use fallback recording.");
      setError(err instanceof Error ? err.message : "Unable to connect voice");
    }
  }

  function onDisconnectVoice() {
    teardownVoiceConnection(true);
  }

  async function startRecording() {
    if (isRecording) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("Audio recording is not supported in this browser.");
      return;
    }

    try {
      setError(null);
      clearRecording();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const chunks: BlobPart[] = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recordingStartedAtRef.current = Date.now();

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      recorder.onstop = () => {
        const elapsed = Math.max(Date.now() - recordingStartedAtRef.current, 1);
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        const previewUrl = URL.createObjectURL(blob);
        setRecordingBlob(blob);
        setRecordingDurationMs(elapsed);
        setRecordingPreviewUrl(previewUrl);
        setIsRecording(false);
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
        mediaRecorderRef.current = null;
      };

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start recording");
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      mediaRecorderRef.current = null;
      setIsRecording(false);
    }
  }

  function stopRecording() {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
  }

  async function onCreateTimelineEvent(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStoryId || !canComposeTimeline) return;

    try {
      setIsSubmittingEvent(true);
      setError(null);
      let audioPayload:
        | {
            audio_ref: string;
            duration_ms: number;
            codec: string;
          }
        | undefined;

      if (recordingBlob) {
        if (!consentedStoryIds.includes(selectedStoryId)) {
          await api.grantVoiceConsent(token, selectedStoryId);
          setConsentedStoryIds((previous) => [...previous, selectedStoryId]);
        }
        const upload = await api.uploadTimelineAudio(
          token,
          selectedStoryId,
          recordingBlob,
          `voice-${Date.now()}.webm`
        );
        audioPayload = {
          audio_ref: upload.audio_ref,
          duration_ms: Math.max(recordingDurationMs, 1),
          codec: recordingBlob.type || "audio/webm"
        };
      }

      const created = await api.createTimelineEvent(token, {
        story_id: selectedStoryId,
        event_type: eventType,
        text_content: eventText.trim() || null,
        language: eventLanguage,
        audio: audioPayload,
        transcript_segments: eventTranscript.trim()
          ? [
              {
                content: eventTranscript.trim(),
                language: eventLanguage
              }
            ]
          : []
      });

      setEvents((previous) => [created, ...previous]);
      setEventText("");
      setEventTranscript("");
      clearRecording();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsSubmittingEvent(false);
    }
  }

  async function onGenerateGmResponse(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStoryId || !canComposeTimeline) return;
    if (!gmPlayerInput.trim()) return;

    try {
      setIsGeneratingGmResponse(true);
      setError(null);
      const generated = await api.respondAsGm(token, {
        story_id: selectedStoryId,
        player_input: gmPlayerInput.trim(),
        language: eventLanguage,
        persist_to_timeline: true
      });
      setLatestGmResponse(generated);
      setGmPlayerInput("");
      if (generated.timeline_event_id) {
        await loadStoryEvents(selectedStoryId, token);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsGeneratingGmResponse(false);
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

        {token && myProgression && (
          <div className="progression-summary stack">
            <h3>My Progression</h3>
            <small>
              Level {myProgression.level} • {myProgression.xp_total} XP
            </small>
            {myProgression.recent_entries.length > 0 ? (
              <ul className="progression-entry-list">
                {myProgression.recent_entries.slice(0, 3).map((entry) => (
                  <li key={entry.id}>
                    <span>+{entry.xp_delta} XP</span>
                    <small>{entry.reason ?? "Story milestone"}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <small>No progression entries yet.</small>
            )}
          </div>
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
        <ul className="story-list">
          {stories.map((story) => (
            <li key={story.id}>
              <button
                className={selectedStoryId === story.id ? "active-story" : ""}
                onClick={() => onSelectStory(story.id)}
                disabled={!token}
              >
                {story.title}
              </button>
            </li>
          ))}
        </ul>

        <div className="story-saves stack">
          <div className="inline">
            <h3>Save Slots</h3>
            <button
              type="button"
              onClick={onRefreshStorySaves}
              disabled={!canManageSelectedStory || isLoadingSaves}
            >
              {isLoadingSaves ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          <small>Host-only administration for save/create/restore.</small>

          {!selectedStoryId ? (
            <p>Select a story to manage saves.</p>
          ) : !canManageSelectedStory ? (
            <p>Read-only companion mode. Host manages save slots.</p>
          ) : (
            <>
              <form onSubmit={onCreateSave} className="stack inline">
                <input
                  value={saveLabel}
                  onChange={(event) => setSaveLabel(event.target.value)}
                  placeholder="Save label"
                  disabled={isCreatingSave || isRestoringSave}
                />
                <button type="submit" disabled={!token || isCreatingSave || isRestoringSave}>
                  {isCreatingSave ? "Saving..." : "Create Save"}
                </button>
              </form>

              {saveStatus && <small className="token-ok">{saveStatus}</small>}

              {saves.length > 0 ? (
                <ul className="save-list">
                  {saves.map((save) => (
                    <li key={save.id}>
                      <button
                        type="button"
                        className={selectedSaveId === save.id ? "active-save" : ""}
                        onClick={() => void onSelectSave(save.id)}
                        disabled={isLoadingSaveDetail || isRestoringSave}
                      >
                        <strong>{save.label}</strong>
                        <span>
                          {save.timeline_event_count} events • {save.session_count} sessions
                        </span>
                        <small>{new Date(save.created_at).toLocaleString()}</small>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No saves yet for this story.</p>
              )}

              {selectedSave && (
                <div className="save-detail stack">
                  <p>
                    Selected save: <strong>{selectedSave.label}</strong>
                  </p>
                  {isLoadingSaveDetail ? (
                    <p>Loading snapshot details...</p>
                  ) : selectedSaveDetail ? (
                    <>
                      <small>
                        Snapshot story: {selectedSaveDetail.snapshot_json.story.title} •
                        {" "}
                        {selectedSaveDetail.snapshot_json.timeline_events.length} events
                      </small>
                      <form onSubmit={onRestoreSave} className="stack">
                        <input
                          value={restoreTitle}
                          onChange={(event) => setRestoreTitle(event.target.value)}
                          placeholder="Restored story title (optional)"
                          disabled={isRestoringSave}
                        />
                        <button type="submit" disabled={!token || isRestoringSave}>
                          {isRestoringSave ? "Restoring..." : "Restore as New Story"}
                        </button>
                      </form>
                    </>
                  ) : (
                    <small>Select a save slot to inspect and restore it.</small>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </section>

      <section className="panel settings-panel">
        <h2>Settings</h2>
        {!token || !settingsDraft ? (
          <p>Authenticate to configure providers and language.</p>
        ) : (
          <form onSubmit={onSaveSettings} className="stack">
            <label className="stack">
              <span>LLM provider</span>
              <select
                value={settingsDraft.llm_provider}
                onChange={(event) =>
                  setSettingsDraft((previous) =>
                    previous
                      ? {
                          ...previous,
                          llm_provider: event.target.value as LlmProvider,
                          llm_model:
                            event.target.value === "ollama" ? previous.llm_model : previous.llm_model ?? null
                        }
                      : previous
                  )
                }
              >
                <option value="codex">Codex</option>
                <option value="claude">Claude</option>
                <option value="ollama">Ollama (local)</option>
              </select>
            </label>

            {settingsDraft.llm_provider === "ollama" && (
              <>
                <div className="timeline-row">
                  <button
                    type="button"
                    onClick={onRefreshOllamaModels}
                    disabled={isLoadingOllamaModels || isSavingSettings}
                  >
                    {isLoadingOllamaModels ? "Refreshing..." : "Refresh Ollama Models"}
                  </button>
                  <small>{ollamaAvailable ? "Local Ollama detected" : "No local Ollama models found"}</small>
                </div>
                <label className="stack">
                  <span>Ollama model</span>
                  <input
                    list="ollama-model-options"
                    value={settingsDraft.llm_model ?? ""}
                    onChange={(event) =>
                      setSettingsDraft((previous) =>
                        previous ? { ...previous, llm_model: event.target.value || null } : previous
                      )
                    }
                    placeholder="e.g. llama3.2:3b"
                  />
                </label>
                <datalist id="ollama-model-options">
                  {ollamaModels.map((model) => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              </>
            )}

            <label className="stack">
              <span>Language</span>
              <select
                value={settingsDraft.language}
                onChange={(event) =>
                  setSettingsDraft((previous) =>
                    previous ? { ...previous, language: event.target.value as AppLanguage } : previous
                  )
                }
              >
                <option value="en">English</option>
                <option value="fr">Francais</option>
              </select>
            </label>

            <label className="stack">
              <span>Voice transport</span>
              <select value={settingsDraft.voice_mode} disabled>
                <option value="webrtc_with_fallback">WebRTC + fallback</option>
              </select>
            </label>

            <button type="submit" disabled={isSavingSettings}>
              {isSavingSettings ? "Saving..." : "Save Settings"}
            </button>
            {settingsStatus && <small>{settingsStatus}</small>}
          </form>
        )}
      </section>

      <section className="panel session-panel">
        <h2>Sessions {selectedStory ? `- ${selectedStory.title}` : ""}</h2>
        {!selectedStoryId ? (
          <p>Select a story first to manage session lobby.</p>
        ) : (
          <>
            {canManageSelectedStory ? (
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
            ) : (
              <p>Read-only companion mode. Host controls session lifecycle.</p>
            )}

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

                <div className="progression-panel stack">
                  <h3>Story Progression</h3>
                  {storyProgressionRows.length > 0 ? (
                    <ul className="progression-row-list">
                      {storyProgressionRows.map((row) => (
                        <li key={row.user_id}>
                          <div className="progression-row-meta">
                            <strong>{row.user_email}</strong>
                            <small>
                              Level {row.level} • {row.xp_total} XP
                            </small>
                          </div>
                          {canManageSelectedStory ? (
                            <div className="progression-row-actions">
                              <input
                                type="number"
                                min={1}
                                max={100000}
                                placeholder="XP"
                                value={xpDraftByUser[row.user_id] ?? ""}
                                onChange={(event) =>
                                  setXpDraftByUser((previous) => ({
                                    ...previous,
                                    [row.user_id]: event.target.value
                                  }))
                                }
                                disabled={awardingUserId === row.user_id}
                              />
                              <input
                                type="text"
                                placeholder="Reason (optional)"
                                value={reasonDraftByUser[row.user_id] ?? ""}
                                onChange={(event) =>
                                  setReasonDraftByUser((previous) => ({
                                    ...previous,
                                    [row.user_id]: event.target.value
                                  }))
                                }
                                disabled={awardingUserId === row.user_id}
                              />
                              <button
                                type="button"
                                onClick={() => void onAwardXp(row.user_id)}
                                disabled={awardingUserId === row.user_id}
                              >
                                {awardingUserId === row.user_id ? "Awarding..." : "Award XP"}
                              </button>
                            </div>
                          ) : (
                            <small>Host updates progression rewards.</small>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <small>No progression rows yet. Start session and join players first.</small>
                  )}
                </div>

                <div className="voice-panel stack">
                  <h3>Voice Channel</h3>
                  {selectedSession.status !== "active" ? (
                    <p>Start the session to enable live WebRTC voice.</p>
                  ) : (
                    <>
                      <div className="timeline-row">
                        {voiceConnectionState === "connected" ? (
                          <button type="button" onClick={onDisconnectVoice}>
                            Disconnect Voice
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={onConnectVoice}
                            disabled={voiceConnectionState === "connecting"}
                          >
                            {voiceConnectionState === "connecting" ? "Connecting..." : "Connect Voice"}
                          </button>
                        )}
                        <small>
                          {voiceStatus ?? "WebRTC live voice. Use timeline recording fallback if unavailable."}
                        </small>
                      </div>

                      {voicePeers.length > 0 ? (
                        <ul className="voice-peer-list">
                          {voicePeers.map((peer) => (
                            <li key={peer.user_id}>
                              <div className="voice-peer-meta">
                                <span>
                                  {peer.user_email} ({peer.role})
                                </span>
                                <small>
                                  {peer.state}
                                  {peer.muted ? " • muted" : ""}
                                </small>
                              </div>
                              {isSelectedSessionHost && peer.role !== "host" ? (
                                <div className="voice-peer-actions">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      sendVoiceModeration(
                                        peer.user_id,
                                        peer.muted ? "unmute" : "mute"
                                      )
                                    }
                                    disabled={voiceConnectionState !== "connected"}
                                  >
                                    {peer.muted ? "Unmute" : "Mute"}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      sendVoiceModeration(peer.user_id, "disconnect")
                                    }
                                    disabled={voiceConnectionState !== "connected"}
                                  >
                                    Disconnect
                                  </button>
                                </div>
                              ) : (
                                <small>{peer.muted ? "Muted by host" : "Active"}</small>
                              )}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <small>No remote peers connected to voice yet.</small>
                      )}
                    </>
                  )}
                </div>

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
          <>
            {canComposeTimeline ? (
              <>
                <form onSubmit={onCreateTimelineEvent} className="stack timeline-composer">
                  <div className="timeline-row">
                    <select
                      value={eventType}
                      onChange={(event) => setEventType(event.target.value as TimelineEventType)}
                      disabled={!token || isSubmittingEvent}
                    >
                      <option value="gm_prompt">GM prompt</option>
                      <option value="player_action">Player action</option>
                      <option value="choice_prompt">Choice prompt</option>
                      <option value="choice_selection">Choice selection</option>
                      <option value="outcome">Outcome</option>
                      <option value="system">System</option>
                    </select>
                    <select
                      value={eventLanguage}
                      onChange={(event) => setEventLanguage(event.target.value)}
                      disabled={!token || isSubmittingEvent}
                    >
                      <option value="en">English</option>
                      <option value="fr">Francais</option>
                    </select>
                  </div>
                  <textarea
                    value={eventText}
                    onChange={(event) => setEventText(event.target.value)}
                    placeholder="Narrative text (optional)"
                    rows={3}
                    disabled={!token || isSubmittingEvent}
                  />
                  <textarea
                    value={eventTranscript}
                    onChange={(event) => setEventTranscript(event.target.value)}
                    placeholder="Transcript text (optional)"
                    rows={2}
                    disabled={!token || isSubmittingEvent}
                  />
                  <div className="timeline-row">
                    {!isRecording ? (
                      <button type="button" onClick={startRecording} disabled={!token || isSubmittingEvent}>
                        Record Audio
                      </button>
                    ) : (
                      <button type="button" onClick={stopRecording} disabled={isSubmittingEvent}>
                        Stop Recording
                      </button>
                    )}
                    {recordingBlob && (
                      <button type="button" onClick={clearRecording} disabled={isSubmittingEvent}>
                        Clear Audio
                      </button>
                    )}
                    <button type="submit" disabled={!token || isSubmittingEvent || isRecording}>
                      {isSubmittingEvent ? "Saving..." : "Add Timeline Event"}
                    </button>
                  </div>
                  {recordingPreviewUrl && (
                    <div className="recording-preview">
                      <audio controls preload="none" src={recordingPreviewUrl} />
                      <small>{Math.round(recordingDurationMs / 1000)}s recorded</small>
                    </div>
                  )}
                </form>

                <form onSubmit={onGenerateGmResponse} className="stack timeline-composer gm-response-form">
                  <label htmlFor="gm-player-input">Generate GM response</label>
                  <textarea
                    id="gm-player-input"
                    value={gmPlayerInput}
                    onChange={(event) => setGmPlayerInput(event.target.value)}
                    placeholder="Player action or question to send to the game master"
                    rows={3}
                    disabled={!token || isGeneratingGmResponse}
                  />
                  <div className="timeline-row">
                    <button
                      type="submit"
                      disabled={
                        !token ||
                        !gmPlayerInput.trim() ||
                        isGeneratingGmResponse ||
                        isSubmittingEvent ||
                        isRecording
                      }
                    >
                      {isGeneratingGmResponse ? "Generating..." : "Generate GM Response"}
                    </button>
                  </div>
                  {latestGmResponse && latestGmResponse.story_id === selectedStoryId && (
                    <div className="gm-response-output">
                      <small>
                        {latestGmResponse.provider}:{latestGmResponse.model} • {latestGmResponse.language}
                      </small>
                      <p>{latestGmResponse.response_text}</p>
                      {latestGmResponse.audio_ref && (
                        <audio controls preload="none" src={latestGmResponse.audio_ref} />
                      )}
                    </div>
                  )}
                </form>
              </>
            ) : (
              <div className="timeline-composer">
                <p>Read-only companion mode. GM controls timeline updates.</p>
              </div>
            )}

            {events.length > 0 ? (
              <div className="timeline-grid">
                {events.map((event) => (
                  <TimelineCard key={event.id} event={event} />
                ))}
              </div>
            ) : (
              <p>No events yet for this story.</p>
            )}
          </>
        ) : (
          <p>Select a story to load timeline events.</p>
        )}
      </section>
    </main>
  );
}
