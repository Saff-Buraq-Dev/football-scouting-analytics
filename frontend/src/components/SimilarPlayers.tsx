import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSimilar, playerSeasonRef, type SimilarityResponse } from "../api";
import { formatMinutes } from "../format";

/** "Players with a similar profile" section of the player page (Phase 9a, D022). */
export function SimilarPlayers({ playerId, seasonId }: { playerId: string; seasonId: string }) {
  const [data, setData] = useState<SimilarityResponse | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setUnavailable(false);
    fetchSimilar(playerId, seasonId, controller.signal)
      .then(setData)
      .catch((e: Error) => e.name !== "AbortError" && setUnavailable(true));
    return () => controller.abort();
  }, [playerId, seasonId]);

  if (unavailable) return null;
  if (!data) return <section className="card empty" style={{ marginTop: 18 }}>Finding similar profiles…</section>;
  const self = playerSeasonRef(playerId, seasonId);

  return (
    <section className="card" style={{ marginTop: 18, padding: 0 }}>
      <div style={{ padding: "16px 18px 6px" }}>
        <h2 className="section-title">Players with a similar profile</h2>
        <p className="theme-note">
          Compared on {data.features.map((f) => f.label.toLowerCase()).join(", ")} among {data.population_size} ranked
          players of the same position group. {data.method_note}
        </p>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Player</th>
            <th className="num">Min</th>
            <th>Closer than</th>
            <th>Main differences</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {data.results.map((p) => (
            <tr key={playerSeasonRef(p.player_id, p.season_id)}>
              <td className="muted">{p.rank}</td>
              <td>
                <Link className="player-link" to={`/players/${p.player_id}/seasons/${p.season_id}`}>{p.player_name}</Link>
                <div className="metric-sub">{p.teams.join(" / ")} · {p.competition}</div>
              </td>
              <td className="num">{formatMinutes(p.minutes)}</td>
              <td>
                <span className="sim-pct">{Math.round(p.similarity_percentile)}%</span>{" "}
                <span className="muted">of the group</span>
              </td>
              <td className="secondary">
                {p.main_differences.map((d) => `${d.direction} ${d.label.toLowerCase()}`).join(", ")}
              </td>
              <td>
                <Link className="button small" to={`/compare?ps=${self}&ps=${playerSeasonRef(p.player_id, p.season_id)}`}>
                  Compare
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
