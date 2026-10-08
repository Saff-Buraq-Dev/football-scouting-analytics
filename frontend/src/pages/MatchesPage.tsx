import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchMatches, fetchSeasons, type MatchListItem, type Season } from "../api";

export function MatchesPage() {
  const [params, setParams] = useSearchParams();
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  const [query, setQuery] = useState("");
  const seasonId = params.get("season") ?? "";

  useEffect(() => {
    const controller = new AbortController();
    fetchSeasons(controller.signal).then((all) => {
      const analysed = all.filter((s) => s.player_count > 0);
      setSeasons(analysed);
      if (!seasonId && analysed.length) {
        setParams({ season: (analysed.find((s) => s.competition === "Premier League") ?? analysed[0]).id }, { replace: true });
      }
    }).catch(() => undefined);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!seasonId) return;
    const controller = new AbortController();
    fetchMatches(seasonId, undefined, controller.signal).then((d) => setMatches(d.matches)).catch(() => undefined);
    return () => controller.abort();
  }, [seasonId]);

  const q = query.trim().toLowerCase();
  const shown = q ? matches.filter((m) => `${m.home_team} ${m.away_team}`.toLowerCase().includes(q)) : matches;
  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Matches</div>
        <h1>Match reports</h1>
        <p>xG race, expected points, team comparison, passing networks and standouts for every match.</p>
      </div>
      <div className="filters">
        <select value={seasonId} onChange={(e) => setParams({ season: e.target.value })} aria-label="League">
          {seasons.map((s) => <option key={s.id} value={s.id}>{s.competition} {s.label}</option>)}
        </select>
        <input type="search" placeholder="Filter by team" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Filter by team" />
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table className="table">
          <thead><tr><th>Date</th><th className="num">Home</th><th className="center">Score</th><th>Away</th></tr></thead>
          <tbody>
            {shown.map((m) => (
              <tr key={m.id}>
                <td className="muted">{m.match_date}{m.matchweek ? ` · MW ${m.matchweek}` : ""}</td>
                <td className="num">{m.home_team}</td>
                <td className="center"><Link className="player-link" to={`/matches/${m.id}`}>{m.home_score} – {m.away_score}</Link></td>
                <td>{m.away_team}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
