// Typed client for the FastAPI backend (src/football_platform/api/app.py).

export type PercentileNote = "unavailable" | "below_minutes_threshold" | "insufficient_attempts" | "not_ranked";
export type ReliabilityBand = "high" | "medium" | "low";

export interface MetricView {
  key: string;
  label: string;
  kind: "count" | "ratio";
  unit: "per_90" | "ratio";
  value: number | null;
  total: number | null;
  percentile: number | null;
  percentile_note: PercentileNote | null;
  regressed: number | null;
  reliability: number | null;
  reliability_band: ReliabilityBand | null;
}

export interface Theme {
  key: string;
  label: string;
  possession_sensitive: boolean;
  metrics: MetricView[];
}

export interface DataSource {
  provider: string;
  notice: string;
}

export interface Profile {
  player: { id: string; name: string; nationality: string | null };
  season: { id: string; label: string; competition: string };
  teams: string[];
  playing_time: {
    minutes: number;
    appearances: number;
    starts: number;
    primary_role: string | null;
    primary_role_share: number | null;
    position_group: string | null;
    eligible: boolean;
    min_minutes: number;
  };
  context: { team_possession_pct: number | null };
  population: { position_group: string | null; size: number | null; seasons: string[]; min_minutes: number };
  themes: Theme[];
  all_metrics: MetricView[];
  data_source: DataSource;
}

export interface SearchResult {
  player_id: string;
  season_id: string;
  player_name: string;
  teams: string[];
  competition: string;
  season_label: string;
  position_group: string | null;
  primary_role: string | null;
  minutes: number;
  eligible: boolean;
}

export interface Season {
  id: string;
  label: string;
  competition: string;
  coverage_scope: string;
  player_count: number;
}

export interface SearchParams {
  q?: string;
  season_id?: string;
  position_group?: string;
  eligible_only?: boolean;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    throw new Error(response.status === 404 ? "not_found" : `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function searchPlayers(params: SearchParams, signal?: AbortSignal) {
  const query = new URLSearchParams();
  if (params.q && params.q.trim().length >= 2) query.set("q", params.q.trim());
  if (params.season_id) query.set("season_id", params.season_id);
  if (params.position_group) query.set("position_group", params.position_group);
  if (params.eligible_only) query.set("eligible_only", "true");
  query.set("limit", "50");
  return getJson<{ results: SearchResult[]; data_source: DataSource }>(`/api/players?${query}`, signal);
}

export function fetchHealth(signal?: AbortSignal) {
  return getJson<{ status: string; analytics_run: { min_minutes: number } | null }>("/api/health", signal);
}

export function fetchSeasons(signal?: AbortSignal) {
  return getJson<Season[]>("/api/seasons", signal);
}

export function fetchProfile(playerId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<Profile>(`/api/players/${playerId}/seasons/${seasonId}`, signal);
}
