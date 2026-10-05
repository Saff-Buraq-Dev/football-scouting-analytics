// Display rules for metrics (docs/FOOTBALL_ANALYTICS.md, "Phase 5 — Player profile").
import type { ComparedMetric, MetricView, PercentileNote, ReliabilityBand, Verdict } from "./api";

// Ratios that read naturally as percentages. npxG per shot stays a decimal (an xG value).
const PERCENT_METRICS = new Set(["pass_completion", "long_pass_share", "aerial_win_pct", "gk_np_save_pct"]);

export const POSITION_GROUP_LABELS: Record<string, string> = {
  goalkeeper: "Goalkeeper",
  centre_back: "Centre-back",
  full_back: "Full-back",
  central_midfield: "Central midfielder",
  attacking_midfield_winger: "Attacking midfielder / winger",
  striker: "Striker",
};

export const POSITION_GROUP_PLURALS: Record<string, string> = {
  goalkeeper: "goalkeepers",
  centre_back: "centre-backs",
  full_back: "full-backs",
  central_midfield: "central midfielders",
  attacking_midfield_winger: "attacking midfielders and wingers",
  striker: "strikers",
};

export const ROLE_LABELS: Record<string, string> = {
  GK: "Goalkeeper", CB: "Centre-back", FB: "Full-back", WB: "Wing-back", DM: "Defensive midfield",
  CM: "Central midfield", WM: "Wide midfield", AM: "Attacking midfield", W: "Winger", CF: "Centre-forward",
};

export const NOTE_TEXT: Record<PercentileNote, string> = {
  unavailable: "Not available from this data source",
  below_minutes_threshold: "Not ranked: below the minutes threshold",
  insufficient_attempts: "Not ranked: too few attempts",
  not_ranked: "Not ranked",
};

export const RELIABILITY_TEXT: Record<ReliabilityBand, string> = {
  high: "High reliability",
  medium: "Medium reliability",
  low: "Low reliability",
};

export function isPercentMetric(key: string): boolean {
  return PERCENT_METRICS.has(key);
}

/** Main value: per 90 for counts, percentage or decimal for ratios. */
export function formatValue(metric: Pick<MetricView, "key" | "unit" | "value">): string {
  if (metric.value === null) return "—";
  if (isPercentMetric(metric.key)) return `${Math.round(metric.value * 100)}%`;
  return metric.value.toFixed(2);
}

/** Season total for counts (integers, or one decimal for xG-type values). */
export function formatTotal(metric: Pick<MetricView, "key" | "unit" | "total">): string | null {
  if (metric.unit !== "per_90" || metric.total === null) return null;
  return Number.isInteger(metric.total) ? `${metric.total}` : metric.total.toFixed(1);
}

export function formatPercentile(percentile: number | null): string {
  return percentile === null ? "—" : `${Math.round(percentile)}`;
}

export function formatMinutes(minutes: number): string {
  return Math.round(minutes).toLocaleString("en-GB");
}

export function formatShare(share: number | null): string {
  return share === null ? "—" : `${Math.round(share * 100)}%`;
}

/** Short display name: last word of the name ("Cesc Fàbregas" -> "Fàbregas"). */
export function shortName(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts[parts.length - 1];
}

/** Plain-language verdict on whether players really differ on a metric (Phase 6). */
export function verdictText(
  metric: Pick<ComparedMetric, "leader" | "pair_verdict">,
  playerNames: string[],
): string {
  const verdict: Verdict = playerNames.length === 2 ? metric.pair_verdict ?? "not_testable" : metric.leader.verdict;
  if (verdict === "clear" && metric.leader.index !== null) {
    return `${shortName(playerNames[metric.leader.index])} clearly ahead`;
  }
  if (verdict === "within_noise") return playerNames.length === 2 ? "Within noise" : "Top two within noise";
  return "Not tested";
}

// Team metrics shown as percentages (shares). Possession is already a percentage value.
const TEAM_SHARE_METRICS = new Set(["long_pass_share", "progressive_pass_share", "counter_npxg_share", "set_piece_npxg_share"]);

export function formatTeamValue(key: string, value: number | null): string {
  if (value === null) return "—";
  if (key === "possession_pct") return `${value.toFixed(1)}%`;
  if (TEAM_SHARE_METRICS.has(key)) return `${Math.round(value * 100)}%`;
  if (key.endsWith("_diff_per_match") || key === "points_vs_expected") return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
  return value.toFixed(2);
}
