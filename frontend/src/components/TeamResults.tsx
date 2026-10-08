import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMatches, type MatchListItem } from "../api";

/** The team's matches of the season, each linking to its match report. */
export function TeamResults({ teamId, seasonId }: { teamId: string; seasonId: string }) {
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    fetchMatches(seasonId, teamId, controller.signal).then((d) => setMatches(d.matches)).catch(() => undefined);
    return () => controller.abort();
  }, [teamId, seasonId]);
  if (matches.length === 0) return null;
  return (
    <details className="card" style={{ marginTop: 18 }}>
      <summary className="section-title" style={{ cursor: "pointer" }}>Results ({matches.length})</summary>
      <table className="table compact">
        <tbody>
          {matches.map((m) => {
            const home = m.home_team_id === teamId;
            const [own, other] = home ? [m.home_score, m.away_score] : [m.away_score, m.home_score];
            const result = own > other ? "W" : own === other ? "D" : "L";
            return (
              <tr key={m.id}>
                <td className="muted">{m.match_date}</td>
                <td>{home ? "vs" : "at"} {home ? m.away_team : m.home_team}</td>
                <td><span className="pill">{result}</span></td>
                <td className="num"><Link className="player-link" to={`/matches/${m.id}`}>{m.home_score} – {m.away_score}</Link></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </details>
  );
}
