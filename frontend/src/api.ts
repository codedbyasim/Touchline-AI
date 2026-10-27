import cacheFile from "./generated/fallback-cache.json";
import type { Club, Lang, Persona } from "./i18n";

export interface Player {
  player_id: string;
  team_id: Club;
  player_name: string;
  shirt_number: number;
  player_role: string;
  baseline_xy: [number, number];
  active_xy: [number, number];
  shift_m: number | null;
}

export interface Badge {
  metric_key: string;
  label: string;
  verified: boolean;
}

export interface Trace {
  agent_id: string;
  name: string;
  role: string;
  stage: string;
  latency_ms: number;
  status: string;
}

export interface Insight {
  mode: string;
  served_from?: string;
  minute: number;
  persona?: Persona;
  language?: Lang;
  favorite_club?: Club;
  spotlight_player_id?: string | null;
  headline: string;
  narrative_body: string;
  why_it_matters: string;
  epistemic_note?: string | null;
  badges: Badge[];
  broadcast_overlay: {
    title: string;
    subtitle: string;
    featured_player_id?: string | null;
    graphic_vectors?: unknown[];
  };
  rhythm_state: string;
  control_vs_chaos_index: number;
  scoreline: { NLR: number; MCB: number };
  positions_22_players?: Player[];
  agent_trace: Trace[];
  handoffs: string[];
  errors?: string[];
  intent?: string;
}

export interface Scrub {
  current_minute: number;
  scoreline: { NLR: number; MCB: number };
  control_vs_chaos_index: number;
  rhythm_state: string;
  positions_22_players: Player[];
  tactical_anomalies: { anomaly_type?: string; metric_proof?: string }[];
  window_comparison?: { baseline_window: string; active_window: string };
}

export interface Recap {
  turning_points: { minute: number; headline: string; narrative_body: string; badges: Badge[]; scoreline: { NLR: number; MCB: number } }[];
  xg: { NLR: number; MCB: number };
  peak_pdr: number;
  tactical_shifts: number;
  scoreline: { NLR: number; MCB: number };
  language: Lang;
}

export interface AutoEvent {
  segment_minute: number;
  fps: number;
  frame_count: number;
  method: string;
  events: Record<string, unknown>[];
  latency_ms?: number;
}

interface CacheFile {
  scrub: Record<string, Scrub>;
  insights: Record<string, Insight>;
  diagnose: Record<string, Insight>;
  recap: Record<string, Recap>;
  auto_event: Record<string, AutoEvent>;
}

const cache = cacheFile as unknown as CacheFile;

export interface Ask {
  minute: number;
  persona: Persona;
  language: Lang;
  favorite_club: Club;
  spotlight_player_id: string;
  custom_question?: string;
}

const TIMEOUT_MS = 30000;

function keyOf(ask: Ask): string {
  return `${ask.minute}|${ask.persona}|${ask.language}|${ask.favorite_club}|${ask.spotlight_player_id || ""}`;
}

export function scrubFrame(minute: number): Scrub | null {
  return cache.scrub[String(minute)] ?? null;
}

export function positionsFor(minute: number, insight?: Insight | null): Player[] {
  if (insight?.positions_22_players?.length) return insight.positions_22_players;
  return scrubFrame(minute)?.positions_22_players ?? [];
}

export function cachedInsight(ask: Ask): Insight | null {
  const hit = cache.insights[keyOf(ask)] || cache.insights[keyOf({ ...ask, spotlight_player_id: "" })];
  if (!hit) return null;
  const frame = scrubFrame(ask.minute);
  return {
    ...hit,
    served_from: "precomputed_cache",
    minute: ask.minute,
    positions_22_players: frame?.positions_22_players ?? [],
    scoreline: hit.scoreline || frame?.scoreline || { NLR: 0, MCB: 0 },
    control_vs_chaos_index: hit.control_vs_chaos_index ?? frame?.control_vs_chaos_index ?? 0,
    rhythm_state: hit.rhythm_state || frame?.rhythm_state || "",
  };
}

export function quietView(minute: number, ask: Ask): Insight {
  const frame = scrubFrame(minute);
  const proof = frame?.tactical_anomalies?.[0]?.metric_proof;
  return {
    mode: "fallback",
    served_from: "precomputed_cache",
    minute,
    persona: ask.persona,
    language: ask.language,
    favorite_club: ask.favorite_club,
    headline: "",
    narrative_body: proof || "",
    why_it_matters: "",
    badges: [],
    broadcast_overlay: { title: "", subtitle: "" },
    rhythm_state: frame?.rhythm_state || "",
    control_vs_chaos_index: frame?.control_vs_chaos_index || 0,
    scoreline: frame?.scoreline || { NLR: 0, MCB: 0 },
    positions_22_players: frame?.positions_22_players || [],
    agent_trace: [],
    handoffs: [],
  };
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!response.ok) throw new Error(String(response.status));
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function analyze(ask: Ask): Promise<Insight> {
  const fallback = cachedInsight(ask) ?? quietView(ask.minute, ask);
  try {
    const live = await post<Insight>("/api/analyze-moment", {
      minute: ask.minute,
      persona: ask.persona,
      language: ask.language,
      favorite_club: ask.favorite_club,
      spotlight_player_id: ask.spotlight_player_id || null,
      custom_question: ask.custom_question || null,
    });
    return { ...live, served_from: "api" };
  } catch {
    return fallback;
  }
}

export async function diagnose(ask: Ask): Promise<Insight> {
  const cacheKey = `${ask.minute}|${ask.favorite_club}|${ask.persona}|${ask.language}`;
  const hit = cache.diagnose[cacheKey];
  const fallback = hit
    ? { ...hit, served_from: "precomputed_cache", positions_22_players: scrubFrame(ask.minute)?.positions_22_players ?? [] }
    : cachedInsight(ask) ?? quietView(ask.minute, ask);
  try {
    const live = await post<Insight>("/api/diagnose-struggle", {
      minute: ask.minute,
      team_id: ask.favorite_club,
      persona: ask.persona,
      language: ask.language,
    });
    return { ...live, served_from: "api" };
  } catch {
    return fallback;
  }
}

export async function fetchRecap(ask: Ask): Promise<Recap | null> {
  const cacheKey = `${ask.persona}|${ask.language}|${ask.favorite_club}`;
  try {
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const response = await fetch(
      `/api/recap?persona=${ask.persona}&language=${ask.language}&favorite_club=${ask.favorite_club}`,
      { signal: ctrl.signal },
    );
    window.clearTimeout(timer);
    if (!response.ok) throw new Error(String(response.status));
    return (await response.json()) as Recap;
  } catch {
    return cache.recap[cacheKey] ?? null;
  }
}

export async function fetchAuto(minute: number): Promise<AutoEvent | null> {
  try {
    return await post<AutoEvent>("/api/auto-event", { segment_minute: minute });
  } catch {
    return cache.auto_event[String(minute)] ?? cache.auto_event["54"] ?? null;
  }
}

export async function fetchTelemetry(minute: number): Promise<Scrub | null> {
  try {
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => ctrl.abort(), 4000);
    const response = await fetch(`/api/telemetry?minute=${minute}`, { signal: ctrl.signal });
    window.clearTimeout(timer);
    if (!response.ok) throw new Error(String(response.status));
    const body = (await response.json()) as Scrub & { badges?: Badge[] };
    return body;
  } catch {
    return scrubFrame(minute);
  }
}

export function overlayDocument(insight: Insight, players: Player[]) {
  return {
    title: insight.headline,
    subtitle: insight.why_it_matters,
    featured_player_id: insight.broadcast_overlay?.featured_player_id ?? null,
    graphic_vectors: players.map((player) => ({
      player_id: player.player_id,
      team_id: player.team_id,
      shirt_number: player.shirt_number,
      from_xy: player.baseline_xy,
      to_xy: player.active_xy,
      shift_m: player.shift_m,
    })),
  };
}
