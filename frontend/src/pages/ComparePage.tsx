import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MAX_COMPARED, fetchComparison, playerSeasonRef, type ComparedMetric, type Comparison } from "../api";
import { PlayerPicker } from "../components/PlayerPicker";
import {
  NOTE_TEXT,
  POSITION_GROUP_LABELS,
  RELIABILITY_TEXT,
  formatMinutes,
  formatPercentile,
  formatValue,
  verdictText,
} from "../format";

const WARNING_TEXT = {
  mixed_position_groups:
    "Players are in different position groups: each percentile is relative to the player's own group. Compare the per-90 values.",
  some_players_not_ranked: "Some players are below the minutes threshold and are not ranked.",
  different_competitions: "Players come from different leagues. League strength is not adjusted.",
};

function seriesVar(index: number) {
  return `var(--series-${index + 1})`;
}

function MetricComparison({ metric, comparison }: { metric: ComparedMetric; comparison: Comparison }) {
  const count = comparison.players.length;
  const verdict = count === 2 ? metric.pair_verdict ?? "not_testable" : metric.leader.verdict;
  return (
    <div className="cmp-metric">
      <div className="cmp-head">
        <span className="metric-name">{metric.label}</span>
        <span className="metric-sub">{metric.unit === "per_90" ? "per 90" : "ratio"}</span>
        <span className={`verdict verdict-${verdict}`}>
          {verdictText(metric, comparison.players.map((p) => p.name))}
        </span>
      </div>
      <div className="cmp-bars">
        {metric.values.map((value, i) => {
          const player = comparison.players[i];
          const isLeader = metric.leader.index === i && metric.leader.verdict === "clear";
          return (
            <div className="cmp-bar-row" key={player.index}>
              {value.percentile !== null ? (
                <div
                  className="cmp-track"
                  tabIndex={0}
                  role="img"
                  aria-label={`${player.name}: ${formatValue(value)}, percentile ${formatPercentile(value.percentile)}`}
                >
                  <div
                    className="cmp-fill"
                    style={{ width: `${Math.max(value.percentile, 1.5)}%`, background: seriesVar(i) }}
                  />
                  <div className="tooltip" role="tooltip">
                    <strong>{player.name}</strong>
                    <dl>
                      <dt>{value.unit === "per_90" ? "Per 90" : "Value"}</dt>
                      <dd>{formatValue(value)}</dd>
                      <dt>Percentile</dt>
                      <dd>{formatPercentile(value.percentile)}</dd>
                      {value.regressed !== null && (
                        <>
                          <dt>Regressed estimate</dt>
                          <dd>
                            {value.regressed.toFixed(2)}
                            {value.regressed_sd !== null && ` ± ${(1.96 * value.regressed_sd).toFixed(2)}`}
                          </dd>
                        </>
                      )}
                      {value.reliability_band && (
                        <>
                          <dt>Reliability</dt>
                          <dd>{RELIABILITY_TEXT[value.reliability_band]}</dd>
                        </>
                      )}
                    </dl>
                  </div>
                </div>
              ) : (
                <div className="cmp-empty">{value.percentile_note ? NOTE_TEXT[value.percentile_note] : "Not ranked"}</div>
              )}
              <span className="cmp-value">
                {formatValue(value)}
                {isLeader && <span className="sr-only"> (clearly ahead)</span>}
              </span>
              <span className="cmp-pct">{formatPercentile(value.percentile)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ComparePage() {
  const [params, setParams] = useSearchParams();
  const refs = params.getAll("ps");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  const setRefs = (next: string[]) => {
    const query = new URLSearchParams();
    next.forEach((ref) => query.append("ps", ref));
    setParams(query, { replace: true });
  };

  useEffect(() => {
    setError(null);
    if (refs.length < 2) {
      setComparison(null);
      return;
    }
    const controller = new AbortController();
    fetchComparison(refs, controller.signal)
      .then(setComparison)
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError("Could not load the comparison.");
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refs.join("|")]);

  const players = comparison?.players ?? [];

  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Player comparison</div>
        <h1>Compare 2 to 4 players</h1>
        <p>
          Bars show percentiles within each player's position group. The verdict says whether a difference is larger
          than the statistical noise of the samples.
        </p>
      </div>

      <div className="cmp-players">
        {players.map((p, i) => (
          <div className="card cmp-player" key={p.index}>
            <span className="swatch" style={{ background: seriesVar(i) }} aria-hidden="true" />
            <div>
              <Link className="player-link" to={`/players/${p.player_id}/seasons/${p.season_id}`}>
                {p.name}
              </Link>
              <div className="metric-sub">
                {p.teams.join(" / ")} · {p.competition}
              </div>
              <div className="metric-sub">
                {p.position_group ? POSITION_GROUP_LABELS[p.position_group] : "—"} · {formatMinutes(p.minutes)} min
                {p.team_possession_pct !== null && ` · team poss. ${Math.round(p.team_possession_pct)}%`}
              </div>
            </div>
            <button
              type="button"
              className="remove"
              aria-label={`Remove ${p.name}`}
              onClick={() => setRefs(refs.filter((r) => r !== playerSeasonRef(p.player_id, p.season_id)))}
            >
              ×
            </button>
          </div>
        ))}
        {refs.length < MAX_COMPARED && (
          <div className="card cmp-add">
            <PlayerPicker exclude={new Set(refs)} onPick={(r) => setRefs([...refs, playerSeasonRef(r.player_id, r.season_id)])} />
            <div className="metric-sub">
              {refs.length}/{MAX_COMPARED} players
            </div>
          </div>
        )}
      </div>

      {refs.length < 2 && <div className="card empty">Add at least two players to compare.</div>}
      {error && <div className="card empty">{error}</div>}

      {comparison && (
        <>
          {comparison.warnings.length > 0 && (
            <div className="notice cmp-warnings">
              {comparison.warnings.map((w) => (
                <div key={w}>{WARNING_TEXT[w]}</div>
              ))}
            </div>
          )}

          <div className="themes">
            {comparison.themes.map((theme) => (
              <section className="card theme" key={theme.key}>
                <h2>{theme.label}</h2>
                <p className="theme-note">
                  {theme.possession_sensitive
                    ? "Defensive volume partly reflects team possession (shown under each player)."
                    : " "}
                </p>
                {theme.metrics.map((metric) => (
                  <MetricComparison key={metric.key} metric={metric} comparison={comparison} />
                ))}
              </section>
            ))}
          </div>
          <p className="muted cmp-rule">
            Verdict rule: {comparison.verdict_rule}. Ratios are not tested. Percentiles describe this season; they are
            not a quality rating.
          </p>
        </>
      )}
    </>
  );
}
