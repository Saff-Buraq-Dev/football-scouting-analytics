import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { fetchSeasons, fetchTeams, type Season, type TeamListItem } from "../api";
import { ScatterMap, type ScatterPoint } from "../components/ScatterMap";
import { formatTeamValue } from "../format";

function points(teams: TeamListItem[], xKey: string, yKey: string, detail: (t: TeamListItem) => string): ScatterPoint[] {
  return teams
    .filter((t) => t.metrics[xKey] !== null && t.metrics[yKey] !== null)
    .map((t) => ({ id: t.team_id, label: t.team_name, x: t.metrics[xKey]!, y: t.metrics[yKey]!, detail: detail(t) }));
}

export function TeamsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [teams, setTeams] = useState<TeamListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const seasonId = params.get("season") ?? "";

  useEffect(() => {
    const controller = new AbortController();
    fetchSeasons(controller.signal)
      .then((all) => {
        const analysed = all.filter((s) => s.player_count > 0);
        setSeasons(analysed);
        if (!seasonId && analysed.length) {
          const pl = analysed.find((s) => s.competition === "Premier League") ?? analysed[0];
          setParams({ season: pl.id }, { replace: true });
        }
      })
      .catch((e: Error) => e.name !== "AbortError" && setError("Could not reach the API. Is it running on port 8000?"));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!seasonId) return;
    const controller = new AbortController();
    fetchTeams(seasonId, controller.signal)
      .then((data) => setTeams(data.teams))
      .catch((e: Error) => e.name !== "AbortError" && setError("Could not load teams."));
    return () => controller.abort();
  }, [seasonId]);

  const open = (teamId: string) => navigate(`/teams/${teamId}/seasons/${seasonId}`);
  // Always label the top three of the table: the teams a reader looks for first.
  const alwaysLabel = useMemo(() => teams.slice(0, 3).map((t) => t.team_id), [teams]);
  const styleMap = useMemo(
    () => points(teams, "possession_pct", "ppda",
      (t) => `possession ${formatTeamValue("possession_pct", t.metrics.possession_pct)} · PPDA ${formatTeamValue("ppda", t.metrics.ppda)} · ${t.points} pts`),
    [teams],
  );
  const qualityMap = useMemo(
    () => points(teams, "npxg_for_per_match", "npxg_against_per_match",
      (t) => `npxG for ${formatTeamValue("npxg_for_per_match", t.metrics.npxg_for_per_match)} · against ${formatTeamValue("npxg_against_per_match", t.metrics.npxg_against_per_match)} per match`),
    [teams],
  );

  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Teams</div>
        <h1>How teams played</h1>
        <p>Style and underlying performance of every team, compared within its league.</p>
      </div>
      <div className="filters">
        <select value={seasonId} onChange={(e) => setParams({ season: e.target.value })} aria-label="League">
          {seasons.map((s) => (
            <option key={s.id} value={s.id}>{s.competition} {s.label}</option>
          ))}
        </select>
      </div>
      {error && <div className="card empty">{error}</div>}

      <div className="themes">
        <ScatterMap
          title="Style: possession and pressing"
          subtitle="Right = more of the ball. Up = more intense pressing (fewer passes allowed per defensive action)."
          points={styleMap}
          x={{ label: "Possession %", format: (v) => `${v.toFixed(0)}%` }}
          y={{ label: "Pressing intensity (PPDA, inverted)", format: (v) => v.toFixed(0), inverted: true }}
          alwaysLabel={alwaysLabel}
          onSelect={open}
        />
        <ScatterMap
          title="Quality: chances created and conceded"
          subtitle="Right = more non-penalty xG created. Up = fewer conceded. Top-right = dominant teams."
          points={qualityMap}
          x={{ label: "npxG for per match", format: (v) => v.toFixed(1) }}
          y={{ label: "npxG against per match (inverted)", format: (v) => v.toFixed(1), inverted: true }}
          alwaysLabel={alwaysLabel}
          onSelect={open}
        />
      </div>

      <div className="card" style={{ padding: 0, marginTop: 18, overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Team</th>
              <th className="num">Pts</th>
              <th className="num">xPts</th>
              <th className="num">Pts − xPts</th>
              <th className="num">GD</th>
              <th className="num">npxG diff / match</th>
              <th className="num">Possession</th>
              <th className="num">PPDA</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((t, i) => {
              const xpts = t.metrics.xpts_per_match === null ? null : t.metrics.xpts_per_match * t.matches;
              return (
                <tr key={t.team_id} className="row-link" onClick={() => open(t.team_id)}>
                  <td className="muted">{i + 1}</td>
                  <td><Link className="player-link" to={`/teams/${t.team_id}/seasons/${seasonId}`} onClick={(e) => e.stopPropagation()}>{t.team_name}</Link></td>
                  <td className="num">{t.points}</td>
                  <td className="num">{xpts === null ? "—" : xpts.toFixed(1)}</td>
                  <td className="num">{xpts === null ? "—" : `${t.points - xpts >= 0 ? "+" : ""}${(t.points - xpts).toFixed(1)}`}</td>
                  <td className="num">{t.goals_for - t.goals_against > 0 ? "+" : ""}{t.goals_for - t.goals_against}</td>
                  <td className="num">{formatTeamValue("npxg_diff_per_match", t.metrics.npxg_diff_per_match)}</td>
                  <td className="num">{formatTeamValue("possession_pct", t.metrics.possession_pct)}</td>
                  <td className="num">{formatTeamValue("ppda", t.metrics.ppda)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted cmp-rule">
        xPts: expected points from every shot's xG (each shot an independent chance). Points above xPts usually mean
        finishing, goalkeeping or luck beyond the underlying chances; in a half-season test, npxG difference predicted
        later points better than past points did.
      </p>
    </>
  );
}
