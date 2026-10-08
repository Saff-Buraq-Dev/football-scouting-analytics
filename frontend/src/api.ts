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

export type Verdict = "clear" | "within_noise" | "not_testable";

export interface ComparedPlayer {
  index: number;
  player_id: string;
  season_id: string;
  name: string;
  teams: string[];
  competition: string;
  season_label: string;
  position_group: string | null;
  primary_role: string | null;
  minutes: number;
  eligible: boolean;
  team_possession_pct: number | null;
  population_size: number | null;
}

export interface ComparedMetric {
  key: string;
  label: string;
  unit: "per_90" | "ratio";
  values: (MetricView & { regressed_sd: number | null })[];
  leader: { index: number | null; verdict: Verdict };
  pair_verdict?: Verdict;
}

export interface Comparison {
  players: ComparedPlayer[];
  same_position_group: boolean;
  warnings: ("mixed_position_groups" | "some_players_not_ranked" | "different_competitions")[];
  themes: { key: string; label: string; possession_sensitive: boolean; metrics: ComparedMetric[] }[];
  verdict_rule: string;
  data_source: DataSource;
}

export const MAX_COMPARED = 4;

export function playerSeasonRef(playerId: string, seasonId: string): string {
  return `${playerId}:${seasonId}`;
}

export function fetchComparison(refs: string[], signal?: AbortSignal) {
  const query = new URLSearchParams();
  refs.forEach((ref) => query.append("ps", ref));
  return getJson<Comparison>(`/api/compare?${query}`, signal);
}

export interface ScoutingPreset {
  key: string;
  label: string;
  position_group: string;
  intent: string;
  criteria: { key: string; label: string; min_percentile: number }[];
}

export interface MetricDefinition {
  key: string;
  label: string;
  kind: "count" | "ratio";
  position_groups: string[] | null;
}

export interface ScoutCriterionValue {
  key: string;
  percentile: number | null;
  value: number | null;
  reliability_band: ReliabilityBand | null;
  passes: boolean;
}

interface ScoutPlayer {
  player_id: string;
  season_id: string;
  player_name: string;
  teams: string[];
  competition: string;
  season_label: string;
  minutes: number;
  team_possession_pct: number | null;
  primary_role: string | null;
  criteria: ScoutCriterionValue[];
}

export interface ScoutResult extends ScoutPlayer {
  rank: number;
  tier: number;
  weakest_percentile: number;
}

export interface NearMiss extends ScoutPlayer {
  gap: number;
  missed: string;
}

export interface ScoutingResponse {
  criteria: { key: string; label: string; min_percentile: number; unit: "per_90" | "ratio" }[];
  population_size: number;
  shortlisted: number;
  tier_1: number;
  results: ScoutResult[];
  near_misses: NearMiss[];
  near_miss_points: number;
  method: string;
  data_source: DataSource;
}

export interface ScoutingQuery {
  position_group: string;
  criteria: { key: string; min_percentile: number }[];
  season_id?: string;
  min_possession?: number;
  max_possession?: number;
}

export function fetchPresets(signal?: AbortSignal) {
  return getJson<ScoutingPreset[]>("/api/scouting/presets", signal);
}

export function fetchMetricDefinitions(signal?: AbortSignal) {
  return getJson<MetricDefinition[]>("/api/metrics", signal);
}

export function runScouting(query: ScoutingQuery, signal?: AbortSignal) {
  const params = new URLSearchParams({ position_group: query.position_group, limit: "60" });
  query.criteria.forEach((c) => params.append("criterion", `${c.key}:${c.min_percentile}`));
  if (query.season_id) params.set("season_id", query.season_id);
  if (query.min_possession !== undefined) params.set("min_possession", String(query.min_possession));
  if (query.max_possession !== undefined) params.set("max_possession", String(query.max_possession));
  return getJson<ScoutingResponse>(`/api/scouting?${params}`, signal);
}

export interface TeamListItem {
  team_id: string;
  season_id: string;
  team_name: string;
  competition: string;
  season_label: string;
  matches: number;
  points: number;
  goals_for: number;
  goals_against: number;
  league_size: number | null;
  metrics: Record<string, number | null>;
}

export interface TeamMetricRow {
  key: string;
  label: string;
  value: number | null;
  percentile: number | null;
  note: string | null;
}

export interface TeamProfile {
  team: Omit<TeamListItem, "metrics">;
  results: TeamMetricRow[];
  points_vs_expected_per_match: number | null;
  style: TeamMetricRow[];
  squad: {
    player_id: string;
    season_id: string;
    player_name: string;
    primary_role: string | null;
    position_group: string | null;
    minutes: number;
    eligible: boolean;
    multiple_clubs: boolean;
  }[];
  population: { description: string; size: number | null };
  data_source: DataSource;
}

export function fetchTeams(seasonId: string, signal?: AbortSignal) {
  return getJson<{ teams: TeamListItem[]; metric_labels: Record<string, string> }>(
    `/api/teams?season_id=${seasonId}`,
    signal,
  );
}

export function fetchTeamProfile(teamId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<TeamProfile>(`/api/teams/${teamId}/seasons/${seasonId}`, signal);
}

export interface SimilarPlayer {
  player_id: string;
  season_id: string;
  player_name: string;
  teams: string[];
  competition: string;
  minutes: number;
  team_possession_pct: number | null;
  rank: number;
  similarity_percentile: number;
  profile_z: number[];
  main_differences: { key: string; label: string; direction: "more" | "fewer"; z_difference: number }[];
}

export interface SimilarityResponse {
  target: { player_id: string; season_id: string; player_name: string; eligible: boolean };
  features: { key: string; label: string; target_z: number }[];
  population_size: number;
  results: SimilarPlayer[];
  method_note: string;
}

export function fetchSimilar(playerId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<SimilarityResponse>(`/api/players/${playerId}/seasons/${seasonId}/similar?limit=10`, signal);
}

export interface ShotZone {
  key: string;
  label: string;
  shots: number;
  goals: number;
  npxg: number;
  npxg_per_shot: number | null;
  share: number;
  baseline_share: number;
  baseline_npxg_per_shot: number | null;
}

export interface ShotZonesView {
  zones: ShotZone[];
  totals: { shots: number; goals: number; npxg: number };
  penalties: { taken: number; scored: number };
}

export function fetchPlayerShots(playerId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<ShotZonesView & { baseline: string }>(`/api/players/${playerId}/seasons/${seasonId}/shots`, signal);
}

export function fetchTeamShots(teamId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<{ for: ShotZonesView; against: ShotZonesView }>(`/api/teams/${teamId}/seasons/${seasonId}/shots`, signal);
}

export interface ZoneCell {
  index: number;
  strip: number;
  channel: string;
  count: number;
  share: number;
  group_share: number;
}

export interface ZoneMapsResponse {
  layout: { strip_edges: number[]; channel_edges: number[]; channels: string[] };
  position_group: string | null;
  maps: { key: "touches" | "receptions" | "progression"; description: string; total: number; zones: ZoneCell[] }[];
}

export function fetchPlayerZones(playerId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<ZoneMapsResponse>(`/api/players/${playerId}/seasons/${seasonId}/zones`, signal);
}

export interface PressingMapsResponse {
  layout: ZoneMapsResponse["layout"];
  maps: { key: "defensive_actions" | "ball_wins"; description: string; total: number; zones: ZoneCell[] }[];
}

export function fetchTeamPressing(teamId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<PressingMapsResponse>(`/api/teams/${teamId}/seasons/${seasonId}/pressing`, signal);
}

export interface MatchListItem {
  id: string;
  season_id: string;
  match_date: string;
  matchweek: number | null;
  home_team_id: string;
  home_team: string;
  away_team_id: string;
  away_team: string;
  home_score: number;
  away_score: number;
  competition: string;
  season_label: string;
}

export interface NetworkNode { player_id: string; name: string; x: number; y: number; involvement: number }

export interface MatchTeamView {
  team_id: string;
  goals: number;
  xg: number;
  npxg: number;
  np_shots: number;
  xpts: number;
  possession_pct: number;
  passes: number;
  progressive_passes: number;
  crosses: number;
  ppda: number | null;
  high_ball_wins: number;
  xt: number | null;
  network: { cutoff_minute: number; cutoff_reason: string; completed_passes: number; small_sample: boolean; nodes: NetworkNode[];
    links: { a: string; b: string; passes: number }[] };
  lineup: { player_id: string; name: string; starter: boolean; minutes: number; shirt: number | null }[];
}

export interface MatchReport {
  match: MatchListItem & { venue: string | null; referee: string | null; stage: string | null };
  home: MatchTeamView;
  away: MatchTeamView;
  xg_race: { minute: number; home_xg: number; away_xg: number; home_goals: number; away_goals: number }[];
  standouts: { key: string; label: string; players: { player_id: string; name: string; team: string; value: number }[] }[];
  notes: { xg_race: string; network: string; xpts: string };
}

export function fetchMatches(seasonId: string, teamId?: string, signal?: AbortSignal) {
  const query = new URLSearchParams({ season_id: seasonId });
  if (teamId) query.set("team_id", teamId);
  return getJson<{ matches: MatchListItem[] }>(`/api/matches?${query}`, signal);
}

export function fetchMatchReport(matchId: string, signal?: AbortSignal) {
  return getJson<MatchReport>(`/api/matches/${matchId}`, signal);
}

export interface CornerSummary {
  corners: number;
  per_match: number | null;
  xg_per_corner: number | null;
  shot_rate: number | null;
  goals: number | null;
  zones: { key: string; label: string; corners: number; share: number; xg_per_corner: number | null; shot_rate: number | null }[];
}

export interface CornerReport {
  for: CornerSummary;
  against: CornerSummary;
  league: CornerSummary;
  notes: { zones: string; outcome: string };
}

export function fetchTeamCorners(teamId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<CornerReport>(`/api/teams/${teamId}/seasons/${seasonId}/corners`, signal);
}

export interface ArchetypeType {
  index: number;
  size: number;
  more: string[];
  less: string[];
  prototypes: { player_id: string; season_id: string; name: string }[];
}

export interface PlayerArchetype {
  position_group: string;
  type: ArchetypeType;
  also_close_to: ArchetypeType | null;
  types_in_group: number;
  note: string;
}

export function fetchArchetypes(signal?: AbortSignal) {
  return getJson<{ groups: Record<string, ArchetypeType[]>; note: string }>("/api/archetypes", signal);
}

export function fetchPlayerArchetype(playerId: string, seasonId: string, signal?: AbortSignal) {
  return getJson<PlayerArchetype>(`/api/players/${playerId}/seasons/${seasonId}/archetype`, signal);
}
