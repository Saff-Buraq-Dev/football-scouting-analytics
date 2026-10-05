import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTeamProfile, fetchTeamShots, type ShotZonesView, type TeamMetricRow, type TeamProfile } from "../api";
import { ShotZoneMap } from "../components/ShotZoneMap";
import { ROLE_LABELS, formatMinutes, formatPercentile, formatTeamValue } from "../format";

function TeamMetric({ row }: { row: TeamMetricRow }) {
  return (
    <div className="metric-row team-metric">
      <div>
        <div className="metric-name">{row.label}</div>
        {row.note && <div className="metric-sub">{row.note}</div>}
      </div>
      {row.percentile === null ? (
        <span className="pbar-empty">{row.value === null ? "Not available from this data source" : "—"}</span>
      ) : (
        <div className="pbar" role="img" aria-label={`${row.label}: percentile ${formatPercentile(row.percentile)} in the league`}>
          <div className="pbar-track">
            <div className="pbar-fill" style={{ width: `${Math.max(row.percentile, 1.5)}%` }} />
            <div className="pbar-median" aria-hidden="true" />
          </div>
        </div>
      )}
      <div className="metric-value">{formatTeamValue(row.key, row.value)}</div>
      <div className="metric-pct">{formatPercentile(row.percentile)}</div>
    </div>
  );
}

export function TeamProfilePage() {
  const { teamId = "", seasonId = "" } = useParams();
  const [profile, setProfile] = useState<TeamProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shots, setShots] = useState<{ for: ShotZonesView; against: ShotZonesView } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setProfile(null);
    fetchTeamProfile(teamId, seasonId, controller.signal)
      .then(setProfile)
      .catch((e: Error) => e.name !== "AbortError" && setError(e.message === "not_found" ? "No analytics for this team." : e.message));
    fetchTeamShots(teamId, seasonId, controller.signal).then(setShots).catch(() => undefined);
    return () => controller.abort();
  }, [teamId, seasonId]);

  if (error) return <div className="card empty">{error}</div>;
  if (!profile) return <div className="card empty">Loading team…</div>;
  const { team } = profile;
  const delta = profile.points_vs_expected_per_match;

  return (
    <>
      <Link className="back" to={`/teams?season=${seasonId}`}>← Teams</Link>
      <section className="card">
        <div className="profile-head">
          <div>
            <div className="eyebrow">{team.competition} · {team.season_label}</div>
            <h1>{team.team_name}</h1>
            <div className="profile-sub">Percentiles within the league ({team.league_size} teams)</div>
          </div>
          <div className="facts">
            <div><div className="fact-label">Points</div><div className="fact-value">{team.points}</div></div>
            <div><div className="fact-label">Goals</div><div className="fact-value">{team.goals_for}–{team.goals_against}</div></div>
            <div><div className="fact-label">Matches</div><div className="fact-value">{team.matches}</div></div>
            <div>
              <div className="fact-label">Pts vs expected</div>
              <div className="fact-value">{delta === null ? "—" : `${delta >= 0 ? "+" : ""}${(delta * team.matches).toFixed(1)}`}</div>
            </div>
          </div>
        </div>
      </section>

      <div className="themes" style={{ marginTop: 18 }}>
        <section className="card theme">
          <h2>Results and underlying performance</h2>
          <p className="theme-note">Per match. Expected points come from the xG of every shot taken and conceded.</p>
          {profile.results.map((row) => <TeamMetric key={row.key} row={row} />)}
        </section>
        <section className="card theme">
          <h2>Playing style</h2>
          <p className="theme-note">Percentiles describe style; they do not rank quality.</p>
          {profile.style.map((row) => <TeamMetric key={row.key} row={row} />)}
        </section>
      </div>

      {shots && (
        <div className="themes" style={{ marginTop: 18 }}>
          <ShotZoneMap title="Shots taken" view={shots.for} baselineLabel="league" />
          <ShotZoneMap title="Shots conceded" view={shots.against} baselineLabel="league" />
        </div>
      )}

      <section className="card" style={{ marginTop: 18, padding: 0 }}>
        <h2 className="section-title" style={{ padding: "16px 18px 0" }}>Squad by minutes</h2>
        <table className="table">
          <thead><tr><th>Player</th><th>Position</th><th className="num">Minutes (season)</th><th /></tr></thead>
          <tbody>
            {profile.squad.map((p) => (
              <tr key={p.player_id}>
                <td><Link className="player-link" to={`/players/${p.player_id}/seasons/${p.season_id}`}>{p.player_name}</Link></td>
                <td className="secondary">{p.primary_role ? ROLE_LABELS[p.primary_role] : "—"}</td>
                <td className="num">{formatMinutes(p.minutes)}</td>
                <td>
                  {p.multiple_clubs && <span className="pill">also another club</span>}{" "}
                  {!p.eligible && <span className="pill">not ranked</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
