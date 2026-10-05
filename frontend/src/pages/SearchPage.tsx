import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { fetchHealth, fetchSeasons, searchPlayers, type SearchResult, type Season } from "../api";
import { POSITION_GROUP_LABELS, ROLE_LABELS, formatMinutes } from "../format";

const DEBOUNCE_MS = 250;

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState(params.get("q") ?? "");
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [minMinutes, setMinMinutes] = useState<number | null>(null);

  const seasonId = params.get("season") ?? "";
  const group = params.get("group") ?? "";
  const eligibleOnly = params.get("ranked") === "1";

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchSeasons(controller.signal).then(setSeasons).catch(() => undefined); // optional filter data
    fetchHealth(controller.signal)
      .then((h) => setMinMinutes(h.analytics_run?.min_minutes ?? null))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      update("q", query.trim());
      searchPlayers({ q: query, season_id: seasonId, position_group: group, eligible_only: eligibleOnly }, controller.signal)
        .then((data) => {
          setResults(data.results);
          setError(null);
        })
        .catch((e: Error) => {
          if (e.name !== "AbortError") setError("Could not reach the API. Is it running on port 8000?");
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, seasonId, group, eligibleOnly]);

  const analysed = seasons.filter((s) => s.player_count > 0);

  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Player search</div>
        <h1>Find a player-season</h1>
        <p>
          Profiles compare each player with others in the same position group across the 2015/16 Premier League,
          La Liga, Serie A and Ligue 1.{minMinutes !== null && ` Players need ${minMinutes} minutes to be ranked.`}
        </p>
      </div>

      <div className="filters" role="search">
        <input
          type="search"
          placeholder="Search a player (e.g. Kanté, Ozil, Buffon)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Player name"
          autoFocus
        />
        <select value={seasonId} onChange={(e) => update("season", e.target.value)} aria-label="Competition">
          <option value="">All competitions</option>
          {analysed.map((s) => (
            <option key={s.id} value={s.id}>
              {s.competition} {s.label}
            </option>
          ))}
        </select>
        <select value={group} onChange={(e) => update("group", e.target.value)} aria-label="Position group">
          <option value="">All positions</option>
          {Object.entries(POSITION_GROUP_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={eligibleOnly} onChange={(e) => update("ranked", e.target.checked ? "1" : "")} />
          Ranked players only
        </label>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {error && <div className="empty">{error}</div>}
        {!error && results !== null && results.length === 0 && <div className="empty">No player-season matches.</div>}
        {!error && results !== null && results.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Club</th>
                <th>Competition</th>
                <th>Position</th>
                <th className="num">Minutes</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const href = `/players/${r.player_id}/seasons/${r.season_id}`;
                return (
                  <tr key={`${r.player_id}-${r.season_id}`} className="row-link" onClick={() => navigate(href)}>
                    <td>
                      <Link className="player-link" to={href} onClick={(e) => e.stopPropagation()}>
                        {r.player_name}
                      </Link>
                    </td>
                    <td className="secondary">{r.teams.join(" / ")}</td>
                    <td className="secondary">
                      {r.competition} <span className="muted">{r.season_label}</span>
                    </td>
                    <td className="secondary">{r.primary_role ? ROLE_LABELS[r.primary_role] : "—"}</td>
                    <td className="num">{formatMinutes(r.minutes)}</td>
                    <td>{!r.eligible && <span className="pill">not ranked</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
