import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

import {
  AppLanguage,
  CharacterCreationMode,
  CharacterInventoryItem,
  CharacterSheet,
  CharacterSpellEntry,
  CharacterSrdOptions,
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
  TtsProvider,
  TtsProviderSummary,
  TimelineEventType,
  UserSettings,
  api,
  Story,
  TimelineEvent
} from "./api";
import { TimelineCard } from "./components/TimelineCard";

const DEVICE_KEY = "dw_device_fingerprint";
const AUTH_SESSION_KEY = "dw_auth_session_v1";
const ACTIVE_STORY_KEY = "dw_active_story_id";
const ABILITY_KEYS = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma"
] as const;
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];

type AbilityKey = (typeof ABILITY_KEYS)[number];

type PersistedAuthSession = {
  token: string;
  user_id: string;
  email: string;
};

function readPersistedAuthSession(): PersistedAuthSession | null {
  const raw = window.localStorage.getItem(AUTH_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PersistedAuthSession>;
    if (
      typeof parsed.token !== "string" ||
      typeof parsed.user_id !== "string" ||
      typeof parsed.email !== "string" ||
      !parsed.token ||
      !parsed.user_id ||
      !parsed.email
    ) {
      return null;
    }
    return {
      token: parsed.token,
      user_id: parsed.user_id,
      email: parsed.email
    };
  } catch {
    return null;
  }
}

function writePersistedAuthSession(session: PersistedAuthSession) {
  window.localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

function clearPersistedAuthSession() {
  window.localStorage.removeItem(AUTH_SESSION_KEY);
}

type CharacterDraft = {
  owner_user_id: string | null;
  name: string;
  race: string;
  character_class: string;
  background: string;
  level: number;
  max_hp: number;
  armor_class: number;
  speed: number;
  creation_mode: CharacterCreationMode;
  ability_rolls: string;
  inventory_text: string;
  spells_text: string;
  notes: string;
  abilities: Record<AbilityKey, string>;
};

function defaultAbilityDraft(): Record<AbilityKey, string> {
  return {
    strength: String(STANDARD_ARRAY[0]),
    dexterity: String(STANDARD_ARRAY[1]),
    constitution: String(STANDARD_ARRAY[2]),
    intelligence: String(STANDARD_ARRAY[3]),
    wisdom: String(STANDARD_ARRAY[4]),
    charisma: String(STANDARD_ARRAY[5])
  };
}

function defaultCharacterDraft(): CharacterDraft {
  return {
    owner_user_id: null,
    name: "",
    race: "Human",
    character_class: "Fighter",
    background: "Soldier",
    level: 1,
    max_hp: 10,
    armor_class: 10,
    speed: 30,
    creation_mode: "auto",
    ability_rolls: "",
    inventory_text: "",
    spells_text: "",
    notes: "",
    abilities: defaultAbilityDraft()
  };
}

function defaultCharacterDraftFromOptions(options: CharacterSrdOptions | null): CharacterDraft {
  const draft = defaultCharacterDraft();
  if (!options) {
    return draft;
  }
  return {
    ...draft,
    owner_user_id: null,
    race: options.races[0] ?? draft.race,
    character_class: options.classes[0] ?? draft.character_class,
    background: options.backgrounds[0] ?? draft.background
  };
}

function getOrCreateDeviceFingerprint() {
  const existing = window.localStorage.getItem(DEVICE_KEY);
  if (existing) return existing;

  const randomPart = window.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
  const created = `device-${randomPart}`;
  window.localStorage.setItem(DEVICE_KEY, created);
  return created;
}

function createTurnId(): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `turn-${Date.now()}-${random}`;
}

function formatSecondsClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function buildWaveformBars(seed: string, bars = 28): number[] {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) % 2147483647;
  }

  const values: number[] = [];
  let cursor = hash || 1;
  for (let index = 0; index < bars; index += 1) {
    cursor = (cursor * 48271) % 2147483647;
    const normalized = cursor / 2147483647;
    values.push(18 + normalized * 74);
  }
  return values;
}

function readTimestampLabel(timestamp: string): string {
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return "--:--";
  }
  return parsed.toLocaleTimeString();
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("Unable to encode blob as data URL"));
      }
    };
    reader.onerror = () => reject(new Error("Unable to read blob data"));
    reader.readAsDataURL(blob);
  });
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

type TurnAudioClip = {
  eventId: string;
  turnId: string;
  eventType: string;
  createdAt: string;
  audioRef: string;
  durationMs: number;
  codec: string;
  transcriptSegments: TimelineEvent["transcript_segments"];
};

type SectionIconName =
  | "spark"
  | "book"
  | "shield"
  | "settings"
  | "users"
  | "timeline"
  | "xp"
  | "qr"
  | "mic"
  | "audio";

function SectionIcon({ name }: { name: SectionIconName }) {
  const strokeProps = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const
  };

  if (name === "spark") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <path {...strokeProps} d="M12 2.8l1.8 4.2L18 8.8 13.8 10.6 12 14.8 10.2 10.6 6 8.8l4.2-1.8z" />
        <path {...strokeProps} d="M18.2 14.8l.9 2 .9-2 2-.9-2-.9-.9-2-.9 2-2 .9z" />
      </svg>
    );
  }
  if (name === "book") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <path {...strokeProps} d="M4.5 19.5A2.5 2.5 0 0 1 7 17h13" />
        <path {...strokeProps} d="M7 3h13v18H7a2.5 2.5 0 0 1-2.5-2.5v-13A2.5 2.5 0 0 1 7 3z" />
      </svg>
    );
  }
  if (name === "shield") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <path {...strokeProps} d="M12 3l7 3v6c0 4.4-3 8.2-7 9-4-.8-7-4.6-7-9V6z" />
      </svg>
    );
  }
  if (name === "settings") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <circle {...strokeProps} cx="12" cy="12" r="3.2" />
        <path {...strokeProps} d="M12 2.5v2.2M12 19.3v2.2M4.7 4.7l1.5 1.5M17.8 17.8l1.5 1.5M2.5 12h2.2M19.3 12h2.2M4.7 19.3l1.5-1.5M17.8 6.2l1.5-1.5" />
      </svg>
    );
  }
  if (name === "users") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <circle {...strokeProps} cx="9" cy="9" r="3" />
        <circle {...strokeProps} cx="17" cy="10.5" r="2.5" />
        <path {...strokeProps} d="M3.5 20c.8-3 3-4.5 5.5-4.5S13.7 17 14.5 20" />
        <path {...strokeProps} d="M14 20c.5-2 2-3.2 4-3.2 1 0 1.9.3 2.7.9" />
      </svg>
    );
  }
  if (name === "timeline") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <path {...strokeProps} d="M4 6h5M11 6h9M4 12h3M9 12h11M4 18h8M14 18h6" />
        <circle {...strokeProps} cx="9" cy="6" r="1.2" />
        <circle {...strokeProps} cx="7" cy="12" r="1.2" />
        <circle {...strokeProps} cx="12" cy="18" r="1.2" />
      </svg>
    );
  }
  if (name === "xp") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <circle {...strokeProps} cx="12" cy="12" r="8" />
        <path {...strokeProps} d="M12 8.5l1.2 2.4 2.6.4-1.9 1.8.5 2.6L12 14.4l-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z" />
      </svg>
    );
  }
  if (name === "qr") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <path {...strokeProps} d="M4 4h5v5H4zM15 4h5v5h-5zM4 15h5v5H4z" />
        <path {...strokeProps} d="M15 15h2v2h-2zM18 18h2v2h-2zM18 15h2v2h-2zM15 18h2v2h-2z" />
      </svg>
    );
  }
  if (name === "mic") {
    return (
      <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
        <rect {...strokeProps} x="9" y="4" width="6" height="10" rx="3" />
        <path {...strokeProps} d="M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v3M9.5 20h5" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className="section-icon" aria-hidden="true">
      <path {...strokeProps} d="M4 13h3l4 4V7l-4 4H4z" />
      <path {...strokeProps} d="M15 10a4 4 0 0 1 0 4M17.5 8a7 7 0 0 1 0 8" />
    </svg>
  );
}

function ButtonLabel({ icon, children }: { icon: SectionIconName; children: ReactNode }) {
  return (
    <span className="button-label">
      <SectionIcon name={icon} />
      <span>{children}</span>
    </span>
  );
}

export function App() {
  const persistedAuth = useMemo(readPersistedAuthSession, []);
  const persistedStoryId = useMemo(() => window.localStorage.getItem(ACTIVE_STORY_KEY), []);
  const initialJoinToken = useMemo(
    () => new URLSearchParams(window.location.search).get("joinToken") ?? "",
    []
  );

  const [email, setEmail] = useState(persistedAuth?.email ?? "gm@example.com");
  const [password, setPassword] = useState("SuperSecret123");
  const [authMode, setAuthMode] = useState<AuthMode>("register");
  const [token, setToken] = useState<string | null>(persistedAuth?.token ?? null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(persistedAuth?.user_id ?? null);
  const [stories, setStories] = useState<Story[]>([]);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(persistedStoryId);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [selectedReplayTurnId, setSelectedReplayTurnId] = useState<string | null>(null);
  const [turnPlaybackState, setTurnPlaybackState] = useState<"idle" | "playing">("idle");
  const [turnPlaybackStatus, setTurnPlaybackStatus] = useState<string | null>(null);
  const [turnPlaybackClipIndex, setTurnPlaybackClipIndex] = useState(-1);
  const [turnPlaybackEventId, setTurnPlaybackEventId] = useState<string | null>(null);
  const [turnPlaybackTimeSec, setTurnPlaybackTimeSec] = useState(0);
  const [turnPlaybackDurationSec, setTurnPlaybackDurationSec] = useState(0);
  const [isExportingTurnPack, setIsExportingTurnPack] = useState(false);
  const [turnExportStatus, setTurnExportStatus] = useState<string | null>(null);
  const [sessions, setSessions] = useState<GameSession[]>([]);
  const [characters, setCharacters] = useState<CharacterSheet[]>([]);
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const [characterSrdOptions, setCharacterSrdOptions] = useState<CharacterSrdOptions | null>(null);
  const [characterDraft, setCharacterDraft] = useState<CharacterDraft>(defaultCharacterDraft);
  const [isLoadingCharacters, setIsLoadingCharacters] = useState(false);
  const [isSavingCharacter, setIsSavingCharacter] = useState(false);
  const [characterStatus, setCharacterStatus] = useState<string | null>(null);
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
  const [ttsProviderCatalog, setTtsProviderCatalog] = useState<TtsProviderSummary[]>([]);
  const [ttsStatus, setTtsStatus] = useState<string | null>(null);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [isValidatingTts, setIsValidatingTts] = useState(false);
  const [isCheckingTtsHealth, setIsCheckingTtsHealth] = useState(false);
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
  const turnAudioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const turnAudioQueueRef = useRef<TurnAudioClip[]>([]);
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

  const selectedCharacter = useMemo(
    () => characters.find((item) => item.id === selectedCharacterId) ?? null,
    [characters, selectedCharacterId]
  );

  const turnReplayOptions = useMemo(() => {
    const grouped = new Map<
      string,
      {
        turnId: string;
        eventCount: number;
        audioCount: number;
        newestAt: string;
      }
    >();

    for (const event of events) {
      const turnId = event.turn_id || event.id;
      const existing = grouped.get(turnId);
      if (existing) {
        existing.eventCount += 1;
        if (event.recording) {
          existing.audioCount += 1;
        }
        if (new Date(event.created_at).getTime() > new Date(existing.newestAt).getTime()) {
          existing.newestAt = event.created_at;
        }
      } else {
        grouped.set(turnId, {
          turnId,
          eventCount: 1,
          audioCount: event.recording ? 1 : 0,
          newestAt: event.created_at
        });
      }
    }

    return Array.from(grouped.values()).sort(
      (a, b) => new Date(b.newestAt).getTime() - new Date(a.newestAt).getTime()
    );
  }, [events]);

  const visibleEvents = useMemo(() => {
    if (!selectedReplayTurnId) {
      return events;
    }
    return events.filter((event) => (event.turn_id || event.id) === selectedReplayTurnId);
  }, [events, selectedReplayTurnId]);

  const selectedTurnEvents = useMemo(
    () =>
      selectedReplayTurnId
        ? events
            .filter((event) => (event.turn_id || event.id) === selectedReplayTurnId)
            .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
        : [],
    [events, selectedReplayTurnId]
  );

  const selectedTurnAudioClips = useMemo<TurnAudioClip[]>(
    () =>
      selectedTurnEvents
        .filter((event) => event.recording !== null)
        .map((event) => ({
          eventId: event.id,
          turnId: event.turn_id || event.id,
          eventType: event.event_type,
          createdAt: event.created_at,
          audioRef: event.recording!.audio_ref,
          durationMs: event.recording!.duration_ms,
          codec: event.recording!.codec,
          transcriptSegments: event.transcript_segments
        })),
    [selectedTurnEvents]
  );

  const selectedTurnAudioTimeline = useMemo(() => {
    let offsetMs = 0;
    return selectedTurnAudioClips.map((clip) => {
      const row = {
        ...clip,
        startOffsetMs: offsetMs
      };
      offsetMs += clip.durationMs;
      return row;
    });
  }, [selectedTurnAudioClips]);

  const orderedCharacters = useMemo(() => {
    const copy = [...characters];
    copy.sort((a, b) => {
      const aMine = a.owner_user_id === currentUserId ? 1 : 0;
      const bMine = b.owner_user_id === currentUserId ? 1 : 0;
      if (aMine !== bMine) {
        return bMine - aMine;
      }
      return a.name.localeCompare(b.name);
    });
    return copy;
  }, [characters, currentUserId]);

  const storyRoster = useMemo(() => {
    const options = new Map<string, string>();
    if (currentUserId) {
      options.set(currentUserId, "You");
    }
    for (const session of sessions) {
      if (selectedStoryId && session.story_id !== selectedStoryId) {
        continue;
      }
      for (const player of session.players) {
        if (!options.has(player.user_id)) {
          const suffix = player.user_id === currentUserId ? " (you)" : "";
          options.set(player.user_id, `${player.user_email}${suffix}`);
        }
      }
    }
    return Array.from(options.entries()).map(([user_id, user_email]) => ({ user_id, user_email }));
  }, [currentUserId, selectedStoryId, sessions]);

  const rosterNameByUserId = useMemo(() => {
    return new Map(storyRoster.map((entry) => [entry.user_id, entry.user_email]));
  }, [storyRoster]);

  const selectedTtsProvider = useMemo(
    () =>
      settingsDraft
        ? ttsProviderCatalog.find((provider) => provider.provider === settingsDraft.tts_provider) ?? null
        : null,
    [settingsDraft, ttsProviderCatalog]
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

  function stopTurnPlayback(statusMessage: string | null = null) {
    const audio = turnAudioPlayerRef.current;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.ontimeupdate = null;
      audio.onloadedmetadata = null;
      audio.pause();
    }
    turnAudioPlayerRef.current = null;
    turnAudioQueueRef.current = [];
    setTurnPlaybackState("idle");
    setTurnPlaybackClipIndex(-1);
    setTurnPlaybackEventId(null);
    setTurnPlaybackTimeSec(0);
    setTurnPlaybackDurationSec(0);
    if (statusMessage !== null) {
      setTurnPlaybackStatus(statusMessage);
    }
  }

  async function playTurnClipByIndex(queue: TurnAudioClip[], index: number) {
    if (index >= queue.length) {
      stopTurnPlayback(`Finished turn playback (${queue.length} clips).`);
      return;
    }

    const clip = queue[index];
    const audio = new Audio(clip.audioRef);
    audio.preload = "auto";
    turnAudioPlayerRef.current = audio;
    setTurnPlaybackState("playing");
    setTurnPlaybackClipIndex(index);
    setTurnPlaybackEventId(clip.eventId);
    setTurnPlaybackDurationSec(Math.max(clip.durationMs, 1) / 1000);
    setTurnPlaybackTimeSec(0);
    setTurnPlaybackStatus(
      `Playing clip ${index + 1}/${queue.length} (${clip.eventType.replace("_", " ")}).`
    );

    audio.onloadedmetadata = () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        setTurnPlaybackDurationSec(audio.duration);
      }
    };
    audio.ontimeupdate = () => {
      setTurnPlaybackTimeSec(audio.currentTime);
    };
    audio.onerror = () => {
      setTurnPlaybackStatus(`Skipped an audio clip due to playback error.`);
      void playTurnClipByIndex(queue, index + 1);
    };
    audio.onended = () => {
      void playTurnClipByIndex(queue, index + 1);
    };

    try {
      await audio.play();
    } catch (err) {
      setTurnPlaybackStatus(
        err instanceof Error ? `Playback blocked: ${err.message}` : "Playback blocked by browser."
      );
      void playTurnClipByIndex(queue, index + 1);
    }
  }

  async function onPlaySelectedTurnAudio() {
    if (!selectedReplayTurnId) {
      setTurnPlaybackStatus("Select a turn before starting autoplay.");
      return;
    }
    if (selectedTurnAudioClips.length === 0) {
      setTurnPlaybackStatus("This turn has no audio clips.");
      return;
    }

    stopTurnPlayback(null);
    turnAudioQueueRef.current = selectedTurnAudioClips;
    await playTurnClipByIndex(selectedTurnAudioClips, 0);
  }

  function onStopTurnAudioPlayback() {
    stopTurnPlayback("Turn playback stopped.");
  }

  async function onExportSelectedTurnPack() {
    if (!selectedReplayTurnId || !selectedStoryId) {
      setTurnExportStatus("Select a turn before exporting.");
      return;
    }
    if (selectedTurnEvents.length === 0) {
      setTurnExportStatus("No timeline data available for this turn.");
      return;
    }

    setIsExportingTurnPack(true);
    setTurnExportStatus(null);
    setError(null);
    try {
      let embeddedAudioCount = 0;
      let audioErrorCount = 0;
      const exportedEvents = await Promise.all(
        selectedTurnEvents.map(async (event) => {
          let exportRecording: Record<string, unknown> | null = null;
          if (event.recording) {
            let audioDataUrl: string | null = null;
            let audioExportError: string | null = null;
            try {
              const response = await fetch(event.recording.audio_ref);
              if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
              }
              const blob = await response.blob();
              audioDataUrl = await blobToDataUrl(blob);
              embeddedAudioCount += 1;
            } catch (err) {
              audioErrorCount += 1;
              audioExportError = err instanceof Error ? err.message : "Unable to download audio";
            }
            exportRecording = {
              id: event.recording.id,
              audio_ref: event.recording.audio_ref,
              duration_ms: event.recording.duration_ms,
              codec: event.recording.codec,
              audio_data_url: audioDataUrl,
              audio_export_error: audioExportError
            };
          }

          return {
            id: event.id,
            turn_id: event.turn_id,
            story_id: event.story_id,
            event_type: event.event_type,
            actor_id: event.actor_id,
            created_at: event.created_at,
            language: event.language,
            text_content: event.text_content,
            source_event_id: event.source_event_id,
            metadata_json: event.metadata_json,
            transcript_segments: event.transcript_segments,
            recording: exportRecording
          };
        })
      );

      const turnPack = {
        version: 1,
        exported_at: new Date().toISOString(),
        story_id: selectedStoryId,
        turn_id: selectedReplayTurnId,
        event_count: exportedEvents.length,
        audio_clip_count: selectedTurnAudioClips.length,
        events: exportedEvents
      };

      const filename = `turn-pack-${selectedReplayTurnId.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
      const blob = new Blob([JSON.stringify(turnPack, null, 2)], {
        type: "application/json"
      });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);

      if (audioErrorCount > 0) {
        setTurnExportStatus(
          `Exported turn pack (${exportedEvents.length} events). ${embeddedAudioCount} audio clips embedded, ${audioErrorCount} failed.`
        );
      } else {
        setTurnExportStatus(
          `Exported turn pack (${exportedEvents.length} events, ${embeddedAudioCount} audio clips embedded).`
        );
      }
    } catch (err) {
      setTurnExportStatus("Export failed.");
      setError(err instanceof Error ? err.message : "Unable to export turn pack");
    } finally {
      setIsExportingTurnPack(false);
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
      stopTurnPlayback(null);
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
    if (!selectedReplayTurnId) {
      stopTurnPlayback(null);
      setTurnPlaybackStatus(null);
      return;
    }
    if (
      turnPlaybackEventId &&
      !selectedTurnAudioClips.some((clip) => clip.eventId === turnPlaybackEventId)
    ) {
      stopTurnPlayback("Turn selection changed. Playback stopped.");
    }
  }, [selectedReplayTurnId, selectedTurnAudioClips, turnPlaybackEventId]);

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

  useEffect(() => {
    if (!selectedCharacter) {
      return;
    }
    hydrateDraftFromCharacter(selectedCharacter);
  }, [selectedCharacter]);

  useEffect(() => {
    if (selectedStoryId) {
      window.localStorage.setItem(ACTIVE_STORY_KEY, selectedStoryId);
    } else {
      window.localStorage.removeItem(ACTIVE_STORY_KEY);
    }
  }, [selectedStoryId]);

  useEffect(() => {
    if (!token || !currentUserId) {
      return;
    }
    const authToken: string = token;

    let cancelled = false;

    async function hydrateAuthenticatedState() {
      try {
        const [loadedStories, loadedSessions] = await Promise.all([
          api.listStories(authToken),
          api.listSessions(authToken)
        ]);
        if (cancelled) {
          return;
        }
        setStories(loadedStories);
        setSessions(loadedSessions);

        await Promise.all([
          loadMyProgression(authToken),
          loadSettings(authToken),
          loadCharacterOptions(authToken)
        ]);
        if (cancelled) {
          return;
        }

        const sessionStoryIds = new Set(loadedSessions.map((session) => session.story_id));
        const nextStoryId =
          selectedStoryId &&
          (loadedStories.some((story) => story.id === selectedStoryId) ||
            sessionStoryIds.has(selectedStoryId))
            ? selectedStoryId
            : loadedStories[0]?.id ?? loadedSessions[0]?.story_id ?? null;
        setSelectedStoryId(nextStoryId);

        setSelectedSessionId((previous) => {
          if (previous && loadedSessions.some((session) => session.id === previous)) {
            return previous;
          }
          if (!nextStoryId) {
            return null;
          }
          return loadedSessions.find((session) => session.story_id === nextStoryId)?.id ?? null;
        });

        if (!nextStoryId) {
          setEvents([]);
          setSelectedReplayTurnId(null);
          setTurnPlaybackStatus(null);
          setTurnExportStatus(null);
          setCharacters([]);
          setSelectedCharacterId(null);
          setSaves([]);
          setSelectedSaveId(null);
          setSelectedSaveDetail(null);
          setStoryProgressionRows([]);
          return;
        }

        await Promise.all([
          loadStoryEvents(nextStoryId, authToken),
          loadStorySessions(nextStoryId, authToken),
          loadStoryCharacters(nextStoryId, authToken),
          loadStorySaves(nextStoryId, authToken),
          loadStoryProgression(nextStoryId, authToken)
        ]);
      } catch (err) {
        if (cancelled) {
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to restore authenticated session.");
        setToken(null);
        setCurrentUserId(null);
        clearPersistedAuthSession();
        window.localStorage.removeItem(ACTIVE_STORY_KEY);
        setStories([]);
        setSessions([]);
        setSelectedStoryId(null);
        setSelectedSessionId(null);
        setJoinBundle(null);
        setEvents([]);
        setSelectedReplayTurnId(null);
        setTurnPlaybackStatus(null);
        setTurnExportStatus(null);
        setCharacters([]);
        setSelectedCharacterId(null);
        setSaves([]);
        setSelectedSaveId(null);
        setSelectedSaveDetail(null);
        setStoryProgressionRows([]);
        setMyProgression(null);
      }
    }

    void hydrateAuthenticatedState();
    return () => {
      cancelled = true;
    };
  }, [token, currentUserId]);

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
    setSelectedReplayTurnId((previous) =>
      previous && loaded.some((event) => (event.turn_id || event.id) === previous) ? previous : null
    );
  }

  async function loadCharacterOptions(authToken: string) {
    const options = await api.listCharacterSrdOptions(authToken);
    setCharacterSrdOptions(options);
    setCharacterDraft((previous) =>
      previous.name.trim() ? previous : defaultCharacterDraftFromOptions(options)
    );
  }

  async function loadStoryCharacters(storyId: string, authToken: string) {
    try {
      setIsLoadingCharacters(true);
      const loaded = await api.listCharacters(authToken, storyId);
      setCharacters(loaded);
      const myCharacterId = currentUserId
        ? loaded.find((item) => item.owner_user_id === currentUserId)?.id ?? null
        : null;
      setSelectedCharacterId((previous) =>
        previous && loaded.some((item) => item.id === previous)
          ? previous
          : myCharacterId ?? loaded[0]?.id ?? null
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (message.includes("Story not found")) {
        setCharacters([]);
        setSelectedCharacterId(null);
        return;
      }
      throw err;
    } finally {
      setIsLoadingCharacters(false);
    }
  }

  async function loadSettings(authToken: string) {
    const [settings, models, ttsProviders] = await Promise.all([
      api.getSettings(authToken),
      api.listOllamaModels(authToken),
      api.listTtsProviders(authToken)
    ]);
    const nextSettings = { ...settings };
    if (models.models.length > 0) {
      const firstModel = models.models[0];
      if (nextSettings.llm_provider === "ollama" && (!nextSettings.llm_model || nextSettings.llm_model === "tts")) {
        nextSettings.llm_model = firstModel;
      }
      if (nextSettings.tts_provider === "ollama" && (!nextSettings.tts_model || nextSettings.tts_model === "tts")) {
        nextSettings.tts_model = firstModel;
      }
    }
    setSettingsDraft(nextSettings);
    setOllamaModels(models.models);
    setOllamaAvailable(models.available);
    setTtsProviderCatalog(ttsProviders.providers);
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

  function parseCharacterAbilityDraft() {
    const parsed = {} as Record<AbilityKey, number>;
    for (const key of ABILITY_KEYS) {
      const raw = characterDraft.abilities[key].trim();
      const value = Number(raw);
      if (!Number.isFinite(value)) {
        throw new Error(`Ability score for ${key} must be numeric.`);
      }
      parsed[key] = Math.floor(value);
    }
    return parsed;
  }

  function parseAbilityRollDraft() {
    if (characterDraft.creation_mode === "auto") {
      return null;
    }
    const parts = characterDraft.ability_rolls
      .split(",")
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0);
    if (parts.length !== 6) {
      throw new Error("Dice modes require six ability rolls separated by commas.");
    }
    return parts.map((entry) => {
      const value = Number(entry);
      if (!Number.isFinite(value)) {
        throw new Error("Each ability roll must be numeric.");
      }
      return Math.floor(value);
    });
  }

  function parseCharacterInventoryDraft(): CharacterInventoryItem[] {
    const lines = characterDraft.inventory_text
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    return lines.map((line, index) => {
      const [rawName, rawQuantity, ...noteParts] = line.split("|").map((part) => part.trim());
      const name = rawName ?? "";
      if (!name) {
        throw new Error(`Inventory line ${index + 1} is missing an item name.`);
      }
      let quantity = 1;
      if (rawQuantity && rawQuantity.length > 0) {
        const parsed = Number(rawQuantity);
        if (!Number.isFinite(parsed) || parsed <= 0) {
          throw new Error(`Inventory line ${index + 1} has an invalid quantity.`);
        }
        quantity = Math.floor(parsed);
      }
      const notes = noteParts.join(" | ").trim();
      return {
        name,
        quantity,
        notes: notes.length > 0 ? notes : null
      };
    });
  }

  function parseCharacterSpellsDraft(): CharacterSpellEntry[] {
    const lines = characterDraft.spells_text
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    return lines.map((line, index) => {
      const [rawName, rawLevel, rawPrepared, rawUses] = line.split("|").map((part) => part.trim());
      const name = rawName ?? "";
      if (!name) {
        throw new Error(`Spell line ${index + 1} is missing a spell name.`);
      }
      let level = 0;
      if (rawLevel && rawLevel.length > 0) {
        const parsedLevel = Number(rawLevel);
        if (!Number.isFinite(parsedLevel) || parsedLevel < 0 || parsedLevel > 9) {
          throw new Error(`Spell line ${index + 1} has an invalid level.`);
        }
        level = Math.floor(parsedLevel);
      }

      const prepared = /^(1|true|yes|y)$/i.test(rawPrepared ?? "");

      let usesRemaining: number | null = null;
      if (rawUses && rawUses.length > 0) {
        const parsedUses = Number(rawUses);
        if (!Number.isFinite(parsedUses) || parsedUses < 0) {
          throw new Error(`Spell line ${index + 1} has an invalid uses value.`);
        }
        usesRemaining = Math.floor(parsedUses);
      }

      return {
        name,
        level,
        prepared,
        uses_remaining: usesRemaining
      };
    });
  }

  function hydrateDraftFromCharacter(character: CharacterSheet) {
    setCharacterDraft({
      owner_user_id: character.owner_user_id,
      name: character.name,
      race: character.race,
      character_class: character.character_class,
      background: character.background,
      level: character.level,
      max_hp: character.max_hp,
      armor_class: character.armor_class,
      speed: character.speed,
      creation_mode: character.creation_mode,
      ability_rolls: character.creation_rolls.join(", "),
      inventory_text: character.inventory
        .map((item) =>
          [item.name, String(item.quantity), item.notes?.trim() || ""]
            .filter((part, index) => index < 2 || part.length > 0)
            .join(" | ")
        )
        .join("\n"),
      spells_text: character.spells
        .map((spell) => {
          const prepared = spell.prepared ? "yes" : "no";
          const uses = spell.uses_remaining === null || spell.uses_remaining === undefined
            ? ""
            : String(spell.uses_remaining);
          return [spell.name, String(spell.level), prepared, uses]
            .filter((part, index) => index < 3 || part.length > 0)
            .join(" | ");
        })
        .join("\n"),
      notes: character.notes ?? "",
      abilities: {
        strength: String(character.abilities.strength ?? 10),
        dexterity: String(character.abilities.dexterity ?? 10),
        constitution: String(character.abilities.constitution ?? 10),
        intelligence: String(character.abilities.intelligence ?? 10),
        wisdom: String(character.abilities.wisdom ?? 10),
        charisma: String(character.abilities.charisma ?? 10)
      }
    });
  }

  async function onCreateCharacter(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStoryId || !canManageSelectedStory) return;
    try {
      setError(null);
      setCharacterStatus(null);
      setIsSavingCharacter(true);
      const abilities = parseCharacterAbilityDraft();
      const abilityRolls = parseAbilityRollDraft();
      const inventory = parseCharacterInventoryDraft();
      const spells = parseCharacterSpellsDraft();
      const created = await api.createCharacter(token, {
        story_id: selectedStoryId,
        owner_user_id: characterDraft.owner_user_id,
        name: characterDraft.name.trim(),
        race: characterDraft.race,
        character_class: characterDraft.character_class,
        background: characterDraft.background,
        level: characterDraft.level,
        max_hp: characterDraft.max_hp,
        armor_class: characterDraft.armor_class,
        speed: characterDraft.speed,
        abilities,
        inventory,
        spells,
        creation_mode: characterDraft.creation_mode,
        ability_rolls: abilityRolls,
        notes: characterDraft.notes.trim() || null
      });
      setCharacters((previous) => [...previous, created]);
      setSelectedCharacterId(created.id);
      setCharacterStatus(`Created character "${created.name}".`);
      hydrateDraftFromCharacter(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create character");
    } finally {
      setIsSavingCharacter(false);
    }
  }

  async function onUpdateCharacter(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedCharacter || !canManageSelectedStory) return;
    try {
      setError(null);
      setCharacterStatus(null);
      setIsSavingCharacter(true);
      const abilities = parseCharacterAbilityDraft();
      const inventory = parseCharacterInventoryDraft();
      const spells = parseCharacterSpellsDraft();
      const updated = await api.updateCharacter(token, selectedCharacter.id, {
        owner_user_id: characterDraft.owner_user_id,
        name: characterDraft.name.trim(),
        race: characterDraft.race,
        character_class: characterDraft.character_class,
        background: characterDraft.background,
        level: characterDraft.level,
        max_hp: characterDraft.max_hp,
        armor_class: characterDraft.armor_class,
        speed: characterDraft.speed,
        abilities,
        inventory,
        spells,
        notes: characterDraft.notes.trim() || null
      });
      setCharacters((previous) =>
        previous.map((item) => (item.id === updated.id ? updated : item))
      );
      setCharacterStatus(`Updated character "${updated.name}".`);
      hydrateDraftFromCharacter(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update character");
    } finally {
      setIsSavingCharacter(false);
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
      writePersistedAuthSession({
        token: response.access_token,
        user_id: response.user.id,
        email
      });
      setJoinBundle(null);
      setRestoreTitle("");
      setSaveStatus(null);
      setSettingsStatus(null);
      setTtsStatus(null);
      setCharacterStatus(null);
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
      if (models.models.length > 0) {
        const firstModel = models.models[0];
        setSettingsDraft((previous) => {
          if (!previous) return previous;
          const next = { ...previous };
          if (next.llm_provider === "ollama" && (!next.llm_model || !models.models.includes(next.llm_model))) {
            next.llm_model = firstModel;
          }
          if (next.tts_provider === "ollama" && (!next.tts_model || !models.models.includes(next.tts_model))) {
            next.tts_model = firstModel;
          }
          return next;
        });
      }
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
        tts_provider: settingsDraft.tts_provider,
        tts_model: settingsDraft.tts_model,
        tts_voice: settingsDraft.tts_voice,
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

  async function onValidateTtsProfile() {
    if (!token || !settingsDraft) return;
    try {
      setError(null);
      setIsValidatingTts(true);
      const validation = await api.validateTtsProfile(token, {
        provider: settingsDraft.tts_provider,
        model: settingsDraft.tts_model,
        voice: settingsDraft.tts_voice
      });
      if (validation.valid) {
        setTtsStatus("TTS profile is valid.");
      } else {
        setTtsStatus(`Validation failed: ${validation.issues.join(" ")}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to validate TTS profile");
    } finally {
      setIsValidatingTts(false);
    }
  }

  async function onCheckTtsHealth() {
    if (!token || !settingsDraft) return;
    try {
      setError(null);
      setIsCheckingTtsHealth(true);
      const health = await api.checkTtsProviderHealth(token, {
        provider: settingsDraft.tts_provider,
        model: settingsDraft.tts_model,
        voice: settingsDraft.tts_voice
      });
      if (health.healthy) {
        setTtsStatus(
          `TTS health check passed for ${health.provider}. ${health.available_models.length} models detected.`
        );
      } else {
        const details = health.issues.length ? health.issues.join(" ") : "Provider did not pass health checks.";
        setTtsStatus(`TTS health check failed: ${details}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to check TTS provider health");
    } finally {
      setIsCheckingTtsHealth(false);
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
      setSelectedReplayTurnId(null);
      setTurnPlaybackStatus(null);
      setTurnExportStatus(null);
      setSessions([]);
      setCharacters([]);
      setSelectedCharacterId(null);
      setSaves([]);
      setStoryProgressionRows([]);
      setSelectedSaveId(null);
      setSelectedSaveDetail(null);
      setRestoreTitle("");
      setSaveStatus(null);
      setCharacterStatus(null);
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
    setSelectedReplayTurnId(null);
    setTurnPlaybackStatus(null);
    setTurnExportStatus(null);
    setJoinBundle(null);
    setCharacters([]);
    setSelectedSaveId(null);
    setSelectedSaveDetail(null);
    setSelectedCharacterId(null);
    setRestoreTitle("");
    setSaveStatus(null);
    setCharacterStatus(null);
    setStoryProgressionRows([]);
    setGmPlayerInput("");
    setLatestGmResponse(null);
    setError(null);
    try {
      await Promise.all([
        loadStoryEvents(storyId, token),
        loadStorySessions(storyId, token),
        loadStoryCharacters(storyId, token),
        loadStorySaves(storyId, token),
        loadStoryProgression(storyId, token)
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  }

  function onStartNewCharacterDraft() {
    setSelectedCharacterId(null);
    setCharacterStatus(null);
    setCharacterDraft({
      ...defaultCharacterDraftFromOptions(characterSrdOptions),
      owner_user_id: currentUserId
    });
  }

  async function onRefreshStoryCharacters() {
    if (!token || !selectedStoryId) return;
    try {
      setError(null);
      await loadStoryCharacters(selectedStoryId, token);
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
      setCharacters([]);
      setSelectedCharacterId(null);
      setRestoreTitle("");
      setSaveStatus(
        `Restored ${restored.timeline_events_restored} events into "${restored.story.title}".`
      );
      setCharacterStatus(null);
      setGmPlayerInput("");
      setLatestGmResponse(null);

      await Promise.all([
        loadStoryEvents(restored.story.id, token),
        loadStorySessions(restored.story.id, token),
        loadStoryCharacters(restored.story.id, token),
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
      setSelectedReplayTurnId(null);
      setTurnPlaybackStatus(null);
      setTurnExportStatus(null);
      setCharacters([]);
      setSelectedCharacterId(null);
      setSaves([]);
      setSelectedSaveId(null);
      setSelectedSaveDetail(null);
      setRestoreTitle("");
      setSaveStatus(null);
      setCharacterStatus(null);
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
              setSelectedReplayTurnId(null);
              setTurnPlaybackStatus(null);
              setTurnExportStatus(null);
            } else {
              throw err;
            }
          }
        })(),
        loadStorySessions(joined.story_id, token),
        loadStoryCharacters(joined.story_id, token),
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
        metadata_json: {
          turn_id: createTurnId(),
          continuity: "manual_timeline_entry"
        },
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
      setSelectedReplayTurnId(created.turn_id || created.id);
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
    const playerInput = gmPlayerInput.trim();
    if (!playerInput) return;

    try {
      setIsGeneratingGmResponse(true);
      setError(null);
      const turnId = createTurnId();
      const sourceEvent = await api.createTimelineEvent(token, {
        story_id: selectedStoryId,
        event_type: "player_action",
        text_content: playerInput,
        language: eventLanguage,
        metadata_json: {
          turn_id: turnId,
          continuity: "gm_response_trigger"
        },
        transcript_segments: [
          {
            content: playerInput,
            language: eventLanguage
          }
        ]
      });
      setEvents((previous) => [sourceEvent, ...previous]);
      const generated = await api.respondAsGm(token, {
        story_id: selectedStoryId,
        player_input: playerInput,
        language: eventLanguage,
        source_event_id: sourceEvent.id,
        turn_id: turnId,
        persist_to_timeline: true
      });
      setLatestGmResponse(generated);
      setGmPlayerInput("");
      setSelectedReplayTurnId(turnId);
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
        <h1 className="title-with-icon app-title">
          <SectionIcon name="spark" />
          <span>DragonWeaver MVP</span>
        </h1>
        <p className="panel-lead">TV host + mobile join by QR token</p>

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
              <ButtonLabel icon="spark">
                {authMode === "register" ? "Register and Enter" : "Login and Enter"}
              </ButtonLabel>
            </button>
          </form>
        ) : (
          <p className="token-ok">Authenticated</p>
        )}

        {token && myProgression && (
          <div className="progression-summary stack">
            <h3 className="title-with-icon section-subtitle">
              <SectionIcon name="xp" />
              <span>My Progression</span>
            </h3>
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
          <h3 className="title-with-icon section-subtitle">
            <SectionIcon name="qr" />
            <span>Mobile Join</span>
          </h3>
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
        <h2 className="title-with-icon section-title">
          <SectionIcon name="book" />
          <span>Stories</span>
        </h2>
        <form onSubmit={onCreateStory} className="stack inline">
          <input
            value={newStoryTitle}
            onChange={(e) => setNewStoryTitle(e.target.value)}
            placeholder="Story title"
          />
          <button type="submit" disabled={!token}>
            <ButtonLabel icon="book">Create</ButtonLabel>
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
            <h3 className="title-with-icon section-subtitle">
              <SectionIcon name="book" />
              <span>Save Slots</span>
            </h3>
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
            <p className="context-hint">Select a story to manage saves.</p>
          ) : !canManageSelectedStory ? (
            <p className="companion-note">Read-only companion mode. Host manages save slots.</p>
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
                  <ButtonLabel icon="book">{isCreatingSave ? "Saving..." : "Create Save"}</ButtonLabel>
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
                          <ButtonLabel icon="book">
                            {isRestoringSave ? "Restoring..." : "Restore as New Story"}
                          </ButtonLabel>
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

      <section className="panel characters-panel">
        <h2 className="title-with-icon section-title">
          <SectionIcon name="shield" />
          <span>Characters {selectedStory ? `- ${selectedStory.title}` : ""}</span>
        </h2>
        {!selectedStoryId ? (
          <p className="context-hint">Select a story to manage character sheets.</p>
        ) : (
          <>
            <div className="inline">
              <button type="button" onClick={onRefreshStoryCharacters} disabled={!token || isLoadingCharacters}>
                {isLoadingCharacters ? "Refreshing..." : "Refresh"}
              </button>
              {canManageSelectedStory && (
                <button type="button" onClick={onStartNewCharacterDraft} disabled={isSavingCharacter}>
                  <ButtonLabel icon="shield">New Character Draft</ButtonLabel>
                </button>
              )}
            </div>

            {characters.length > 0 ? (
              <ul className="character-list">
                {orderedCharacters.map((character) => (
                  <li key={character.id}>
                    <button
                      type="button"
                      className={selectedCharacterId === character.id ? "active-character" : ""}
                      onClick={() => setSelectedCharacterId(character.id)}
                    >
                      <strong>
                        {character.name}
                        {character.owner_user_id === currentUserId ? (
                          <span className="character-badge">Mine</span>
                        ) : null}
                      </strong>
                      <span>
                        L{character.level} {character.race} {character.character_class}
                      </span>
                      <small>
                        Owner:{" "}
                        {character.owner_user_id
                          ? rosterNameByUserId.get(character.owner_user_id) ?? character.owner_user_id
                          : "Unassigned"}
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No character sheets yet for this story.</p>
            )}

            {selectedCharacter && (
              <div className="character-summary stack">
                <small>
                  HP {selectedCharacter.current_hp}/{selectedCharacter.max_hp} • AC {selectedCharacter.armor_class} •
                  {" "}
                  Speed {selectedCharacter.speed} • Prof +{selectedCharacter.proficiency_bonus}
                </small>
                <small>
                  Owner:{" "}
                  {selectedCharacter.owner_user_id
                    ? rosterNameByUserId.get(selectedCharacter.owner_user_id) ?? selectedCharacter.owner_user_id
                    : "Unassigned"}
                </small>
                <div className="character-abilities-grid">
                  {ABILITY_KEYS.map((key) => (
                    <small key={key}>
                      {key.slice(0, 3).toUpperCase()} {selectedCharacter.abilities[key] ?? "-"}
                    </small>
                  ))}
                </div>
                {selectedCharacter.inventory.length > 0 ? (
                  <div className="character-detail-list">
                    <small>Inventory</small>
                    <ul>
                      {selectedCharacter.inventory.map((item, index) => (
                        <li key={`${item.name}-${index}`}>
                          {item.name} x{item.quantity}
                          {item.notes ? ` - ${item.notes}` : ""}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <small>Inventory empty.</small>
                )}
                {selectedCharacter.spells.length > 0 ? (
                  <div className="character-detail-list">
                    <small>Spells</small>
                    <ul>
                      {selectedCharacter.spells.map((spell, index) => (
                        <li key={`${spell.name}-${index}`}>
                          {spell.name} (L{spell.level})
                          {spell.prepared ? " prepared" : ""}
                          {spell.uses_remaining !== null && spell.uses_remaining !== undefined
                            ? ` uses ${spell.uses_remaining}`
                            : ""}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <small>No spells listed.</small>
                )}
              </div>
            )}

            {canManageSelectedStory ? (
              <form
                onSubmit={selectedCharacter ? onUpdateCharacter : onCreateCharacter}
                className="stack character-form"
              >
                <input
                  value={characterDraft.name}
                  onChange={(event) =>
                    setCharacterDraft((previous) => ({ ...previous, name: event.target.value }))
                  }
                  placeholder="Character name"
                  disabled={isSavingCharacter}
                />
                <label className="stack">
                  <span>Character owner</span>
                  <select
                    value={characterDraft.owner_user_id ?? ""}
                    onChange={(event) =>
                      setCharacterDraft((previous) => ({
                        ...previous,
                        owner_user_id: event.target.value || null
                      }))
                    }
                    disabled={isSavingCharacter}
                  >
                    <option value="">Unassigned</option>
                    {storyRoster.map((entry) => (
                      <option key={entry.user_id} value={entry.user_id}>
                        {entry.user_email}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="timeline-row">
                  <select
                    value={characterDraft.race}
                    onChange={(event) =>
                      setCharacterDraft((previous) => ({ ...previous, race: event.target.value }))
                    }
                    disabled={isSavingCharacter}
                  >
                    {(characterSrdOptions?.races ?? ["Human"]).map((race) => (
                      <option key={race} value={race}>
                        {race}
                      </option>
                    ))}
                  </select>
                  <select
                    value={characterDraft.character_class}
                    onChange={(event) =>
                      setCharacterDraft((previous) => ({
                        ...previous,
                        character_class: event.target.value
                      }))
                    }
                    disabled={isSavingCharacter}
                  >
                    {(characterSrdOptions?.classes ?? ["Fighter"]).map((className) => (
                      <option key={className} value={className}>
                        {className}
                      </option>
                    ))}
                  </select>
                  <select
                    value={characterDraft.background}
                    onChange={(event) =>
                      setCharacterDraft((previous) => ({
                        ...previous,
                        background: event.target.value
                      }))
                    }
                    disabled={isSavingCharacter}
                  >
                    {(characterSrdOptions?.backgrounds ?? ["Soldier"]).map((background) => (
                      <option key={background} value={background}>
                        {background}
                      </option>
                    ))}
                  </select>
                </div>

                {!selectedCharacter && (
                  <>
                    <label className="stack">
                      <span>Creation mode</span>
                      <select
                        value={characterDraft.creation_mode}
                        onChange={(event) =>
                          setCharacterDraft((previous) => ({
                            ...previous,
                            creation_mode: event.target.value as CharacterCreationMode
                          }))
                        }
                        disabled={isSavingCharacter}
                      >
                        <option value="auto">Auto (standard array)</option>
                        <option value="player_dice">Player dice</option>
                        <option value="gm_dice">GM dice (TV)</option>
                      </select>
                    </label>
                    {characterDraft.creation_mode !== "auto" && (
                      <input
                        value={characterDraft.ability_rolls}
                        onChange={(event) =>
                          setCharacterDraft((previous) => ({
                            ...previous,
                            ability_rolls: event.target.value
                          }))
                        }
                        placeholder="Ability rolls (ex: 15,14,13,12,10,8)"
                        disabled={isSavingCharacter}
                      />
                    )}
                  </>
                )}

                <div className="ability-grid">
                  {ABILITY_KEYS.map((key) => (
                    <label key={key} className="stack">
                      <span>{key.slice(0, 3).toUpperCase()}</span>
                      <input
                        type="number"
                        value={characterDraft.abilities[key]}
                        onChange={(event) =>
                          setCharacterDraft((previous) => ({
                            ...previous,
                            abilities: {
                              ...previous.abilities,
                              [key]: event.target.value
                            }
                          }))
                        }
                        disabled={isSavingCharacter}
                      />
                    </label>
                  ))}
                </div>

                <div className="timeline-row">
                  <label className="stack">
                    <span>Level</span>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={characterDraft.level}
                      onChange={(event) =>
                        setCharacterDraft((previous) => ({
                          ...previous,
                          level: Number(event.target.value)
                        }))
                      }
                      disabled={isSavingCharacter}
                    />
                  </label>
                  <label className="stack">
                    <span>Max HP</span>
                    <input
                      type="number"
                      min={1}
                      value={characterDraft.max_hp}
                      onChange={(event) =>
                        setCharacterDraft((previous) => ({
                          ...previous,
                          max_hp: Number(event.target.value)
                        }))
                      }
                      disabled={isSavingCharacter}
                    />
                  </label>
                  <label className="stack">
                    <span>AC</span>
                    <input
                      type="number"
                      min={1}
                      value={characterDraft.armor_class}
                      onChange={(event) =>
                        setCharacterDraft((previous) => ({
                          ...previous,
                          armor_class: Number(event.target.value)
                        }))
                      }
                      disabled={isSavingCharacter}
                    />
                  </label>
                  <label className="stack">
                    <span>Speed</span>
                    <input
                      type="number"
                      min={0}
                      value={characterDraft.speed}
                      onChange={(event) =>
                        setCharacterDraft((previous) => ({
                          ...previous,
                          speed: Number(event.target.value)
                        }))
                      }
                      disabled={isSavingCharacter}
                    />
                  </label>
                </div>

                <textarea
                  value={characterDraft.notes}
                  onChange={(event) =>
                    setCharacterDraft((previous) => ({ ...previous, notes: event.target.value }))
                  }
                  placeholder="Character notes (optional)"
                  rows={2}
                  disabled={isSavingCharacter}
                />
                <label className="stack">
                  <span>Inventory (one line per item: name | qty | notes)</span>
                  <textarea
                    value={characterDraft.inventory_text}
                    onChange={(event) =>
                      setCharacterDraft((previous) => ({
                        ...previous,
                        inventory_text: event.target.value
                      }))
                    }
                    rows={3}
                    placeholder={"Longsword | 1 | silvered\nPotion of Healing | 2"}
                    disabled={isSavingCharacter}
                  />
                </label>
                <label className="stack">
                  <span>Spells (one line: name | level | prepared yes/no | uses)</span>
                  <textarea
                    value={characterDraft.spells_text}
                    onChange={(event) =>
                      setCharacterDraft((previous) => ({
                        ...previous,
                        spells_text: event.target.value
                      }))
                    }
                    rows={3}
                    placeholder={"Magic Missile | 1 | yes |\nShield | 1 | yes | 3"}
                    disabled={isSavingCharacter}
                  />
                </label>
                <button type="submit" disabled={!token || isSavingCharacter || !characterDraft.name.trim()}>
                  <ButtonLabel icon="shield">
                    {isSavingCharacter
                      ? "Saving..."
                      : selectedCharacter
                        ? "Update Character"
                        : "Create Character"}
                  </ButtonLabel>
                </button>
                {characterStatus && <small className="token-ok">{characterStatus}</small>}
              </form>
            ) : (
              <p className="companion-note">
                Read-only companion mode. Host controls character sheet edits.
                {selectedCharacter?.owner_user_id === currentUserId
                  ? " This is your assigned character."
                  : ""}
              </p>
            )}
          </>
        )}
      </section>

      <section className="panel settings-panel">
        <h2 className="title-with-icon section-title">
          <SectionIcon name="settings" />
          <span>Settings</span>
        </h2>
        {!token || !settingsDraft ? (
          <p className="context-hint">Authenticate to configure providers and language.</p>
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
                            event.target.value === "ollama"
                              ? previous.llm_model || ollamaModels[0] || null
                              : previous.llm_model ?? null
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
                    placeholder={ollamaModels[0] ?? "e.g. model:tag"}
                  />
                </label>
                <datalist id="ollama-model-options">
                  {ollamaModels.map((model) => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              </>
            )}

            <hr />

            <label className="stack">
              <span>TTS provider</span>
              <select
                value={settingsDraft.tts_provider}
                onChange={(event) => {
                  const nextProvider = event.target.value as TtsProvider;
                  setSettingsDraft((previous) => {
                    if (!previous) return previous;
                    const providerConfig = ttsProviderCatalog.find(
                      (provider) => provider.provider === nextProvider
                    );
                    return {
                      ...previous,
                      tts_provider: nextProvider,
                      tts_model:
                        providerConfig && previous.tts_provider !== nextProvider
                          ? nextProvider === "ollama"
                            ? ollamaModels[0] || providerConfig.default_model
                            : providerConfig.default_model
                          : previous.tts_model,
                      tts_voice:
                        providerConfig && previous.tts_provider !== nextProvider
                          ? providerConfig.default_voice
                          : previous.tts_voice
                    };
                  });
                  setTtsStatus(null);
                }}
              >
                <option value="codex">Codex</option>
                <option value="claude">Claude</option>
                <option value="ollama">Ollama (local)</option>
              </select>
              <small>
                {selectedTtsProvider?.configured
                  ? "Provider configured in backend environment."
                  : "Provider not configured in backend environment. Deterministic fallback will be used."}
              </small>
            </label>

            <label className="stack">
              <span>TTS model</span>
              <input
                value={settingsDraft.tts_model ?? ""}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  setSettingsDraft((previous) =>
                    previous ? { ...previous, tts_model: nextValue ? nextValue : null } : previous
                  );
                  setTtsStatus(null);
                }}
                placeholder={selectedTtsProvider?.default_model ?? "tts model"}
                list={settingsDraft.tts_provider === "ollama" ? "tts-ollama-model-options" : undefined}
              />
            </label>
            {settingsDraft.tts_provider === "ollama" && (
              <datalist id="tts-ollama-model-options">
                {ollamaModels.map((model) => (
                  <option key={model} value={model} />
                ))}
              </datalist>
            )}

            <label className="stack">
              <span>TTS voice</span>
              <input
                value={settingsDraft.tts_voice}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  setSettingsDraft((previous) =>
                    previous ? { ...previous, tts_voice: nextValue || previous.tts_voice } : previous
                  );
                  setTtsStatus(null);
                }}
                placeholder={selectedTtsProvider?.default_voice ?? "alloy"}
                list={`tts-voice-options-${settingsDraft.tts_provider}`}
              />
            </label>
            <datalist id={`tts-voice-options-${settingsDraft.tts_provider}`}>
              {(selectedTtsProvider?.supported_voices ?? []).map((voice) => (
                <option key={voice} value={voice} />
              ))}
            </datalist>

            <div className="timeline-row">
              <button
                type="button"
                onClick={onValidateTtsProfile}
                disabled={isValidatingTts || isSavingSettings || isCheckingTtsHealth}
              >
                {isValidatingTts ? "Validating..." : "Validate TTS"}
              </button>
              <button
                type="button"
                onClick={onCheckTtsHealth}
                disabled={isCheckingTtsHealth || isSavingSettings || isValidatingTts}
              >
                {isCheckingTtsHealth ? "Checking..." : "Run TTS Health Check"}
              </button>
            </div>
            {ttsStatus && <small>{ttsStatus}</small>}

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
              <ButtonLabel icon="settings">{isSavingSettings ? "Saving..." : "Save Settings"}</ButtonLabel>
            </button>
            {settingsStatus && <small>{settingsStatus}</small>}
          </form>
        )}
      </section>

      <section className="panel session-panel">
        <h2 className="title-with-icon section-title">
          <SectionIcon name="users" />
          <span>Sessions {selectedStory ? `- ${selectedStory.title}` : ""}</span>
        </h2>
        {!selectedStoryId ? (
          <p className="context-hint">Select a story first to manage session lobby.</p>
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
                  <ButtonLabel icon="users">New Session</ButtonLabel>
                </button>
              </form>
            ) : (
              <p className="companion-note">Read-only companion mode. Host controls session lifecycle.</p>
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
                      <ButtonLabel icon="qr">Start + Generate QR Token</ButtonLabel>
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
                  <h3 className="title-with-icon section-subtitle">
                    <SectionIcon name="xp" />
                    <span>Story Progression</span>
                  </h3>
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
                  <h3 className="title-with-icon section-subtitle">
                    <SectionIcon name="mic" />
                    <span>Voice Channel</span>
                  </h3>
                  {selectedSession.status !== "active" ? (
                    <p className="context-hint">Start the session to enable live WebRTC voice.</p>
                  ) : (
                    <>
                      <div className="timeline-row">
                        {voiceConnectionState === "connected" ? (
                          <button type="button" onClick={onDisconnectVoice}>
                            <ButtonLabel icon="mic">Disconnect Voice</ButtonLabel>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={onConnectVoice}
                            disabled={voiceConnectionState === "connecting"}
                          >
                            <ButtonLabel icon="mic">
                              {voiceConnectionState === "connecting" ? "Connecting..." : "Connect Voice"}
                            </ButtonLabel>
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
        <h2 className="title-with-icon section-title">
          <SectionIcon name="timeline" />
          <span>Timeline {selectedStory ? `- ${selectedStory.title}` : ""}</span>
        </h2>
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
                      <ButtonLabel icon="timeline">
                        {isSubmittingEvent ? "Saving..." : "Add Timeline Event"}
                      </ButtonLabel>
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
                      <ButtonLabel icon="spark">
                        {isGeneratingGmResponse ? "Generating..." : "Generate GM Response"}
                      </ButtonLabel>
                    </button>
                  </div>
                  {latestGmResponse && latestGmResponse.story_id === selectedStoryId && (
                    <div className="gm-response-output">
                      <small>
                        {latestGmResponse.provider}:{latestGmResponse.model} • {latestGmResponse.language}
                      </small>
                      {latestGmResponse.audio_provider && latestGmResponse.audio_model && (
                        <small>
                          TTS: {latestGmResponse.audio_provider}:{latestGmResponse.audio_model}
                        </small>
                      )}
                      {latestGmResponse.turn_id && (
                        <small>Turn: {latestGmResponse.turn_id}</small>
                      )}
                      {latestGmResponse.source_event_id && (
                        <small>Linked player event: {latestGmResponse.source_event_id.slice(0, 8)}</small>
                      )}
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
                <p className="companion-note">Read-only companion mode. GM controls timeline updates.</p>
              </div>
            )}

            {turnReplayOptions.length > 0 && (
              <div className="turn-replay-panel stack">
                <div className="timeline-row">
                  <label htmlFor="turn-replay-select">Turn replay</label>
                  <select
                    id="turn-replay-select"
                    value={selectedReplayTurnId ?? ""}
                    onChange={(event) => {
                      setSelectedReplayTurnId(event.target.value || null);
                    }}
                  >
                    <option value="">All turns</option>
                    {turnReplayOptions.map((option) => (
                      <option key={option.turnId} value={option.turnId}>
                        {new Date(option.newestAt).toLocaleTimeString()} • {option.eventCount} events •{" "}
                        {option.audioCount} audio
                      </option>
                    ))}
                  </select>
                  {selectedReplayTurnId && (
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedReplayTurnId(null);
                      }}
                    >
                      Clear
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void onPlaySelectedTurnAudio()}
                    disabled={!selectedReplayTurnId || selectedTurnAudioClips.length === 0 || turnPlaybackState === "playing"}
                  >
                    <ButtonLabel icon="audio">
                      {turnPlaybackState === "playing" ? "Playing..." : "Play Turn Audio"}
                    </ButtonLabel>
                  </button>
                  <button
                    type="button"
                    onClick={onStopTurnAudioPlayback}
                    disabled={turnPlaybackState !== "playing"}
                  >
                    Stop
                  </button>
                  <button
                    type="button"
                    onClick={() => void onExportSelectedTurnPack()}
                    disabled={!selectedReplayTurnId || selectedTurnEvents.length === 0 || isExportingTurnPack}
                  >
                    <ButtonLabel icon="audio">
                      {isExportingTurnPack ? "Exporting..." : "Export Turn Pack"}
                    </ButtonLabel>
                  </button>
                </div>
                <small>
                  {selectedReplayTurnId
                    ? "Filtered to a single voice/text turn for replay continuity."
                    : "Select a turn to focus synchronized transcript + audio replay."}
                </small>
                {turnPlaybackState === "playing" && (
                  <small>
                    Clip {turnPlaybackClipIndex + 1}/{selectedTurnAudioClips.length} •{" "}
                    {formatSecondsClock(turnPlaybackTimeSec)} / {formatSecondsClock(turnPlaybackDurationSec)}
                  </small>
                )}
                {turnPlaybackStatus && <small>{turnPlaybackStatus}</small>}
                {turnExportStatus && <small>{turnExportStatus}</small>}
              </div>
            )}

            {selectedReplayTurnId && selectedTurnAudioTimeline.length > 0 && (
              <div className="turn-waveform-panel stack">
                <h3 className="title-with-icon section-subtitle">
                  <SectionIcon name="audio" />
                  <span>Turn Audio Timeline</span>
                </h3>
                {selectedTurnAudioTimeline.map((clip) => {
                  const waveformBars = buildWaveformBars(
                    `${clip.turnId}:${clip.eventId}:${clip.audioRef}:${clip.codec}`
                  );
                  const progressRatio =
                    turnPlaybackEventId === clip.eventId && turnPlaybackDurationSec > 0
                      ? Math.min(turnPlaybackTimeSec / turnPlaybackDurationSec, 1)
                      : 0;

                  return (
                    <div
                      key={clip.eventId}
                      className={`turn-waveform-row${
                        turnPlaybackEventId === clip.eventId ? " turn-waveform-row-active" : ""
                      }`}
                    >
                      <div className="turn-waveform-meta">
                        <strong>{clip.eventType.replace("_", " ")}</strong>
                        <small>
                          +{formatSecondsClock(clip.startOffsetMs / 1000)} •{" "}
                          {Math.round(clip.durationMs / 1000)}s • {clip.codec}
                        </small>
                      </div>
                      <div className="turn-waveform-track" aria-label={`Waveform for ${clip.eventType}`}>
                        {waveformBars.map((height, barIndex) => {
                          const played = barIndex / waveformBars.length < progressRatio;
                          return (
                            <span
                              key={`${clip.eventId}-${barIndex}`}
                              className={played ? "played" : ""}
                              style={{ height: `${height}%` }}
                            />
                          );
                        })}
                      </div>
                      {clip.transcriptSegments.length > 0 && (
                        <ul className="turn-transcript-list">
                          {clip.transcriptSegments.map((segment) => (
                            <li key={segment.id}>
                              <small>{readTimestampLabel(segment.timestamp)}</small>
                              <span>{segment.content}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {events.length > 0 ? (
              <div className="timeline-grid">
                {visibleEvents.map((event) => (
                  <TimelineCard
                    key={event.id}
                    event={event}
                    replayFocused={selectedReplayTurnId === (event.turn_id || event.id)}
                    onReplayTurn={(turnId) => {
                      setSelectedReplayTurnId(turnId);
                    }}
                    activeAudioEventId={turnPlaybackEventId}
                  />
                ))}
              </div>
            ) : (
              <p className="context-hint">No events yet for this story.</p>
            )}
          </>
        ) : (
          <p className="context-hint">Select a story to load timeline events.</p>
        )}
      </section>
    </main>
  );
}
