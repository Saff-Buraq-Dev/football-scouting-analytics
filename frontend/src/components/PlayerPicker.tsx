import { useEffect, useState } from "react";
import { searchPlayers, type SearchResult } from "../api";
import { ROLE_LABELS, formatMinutes } from "../format";

const DEBOUNCE_MS = 250;

/** Search box that adds a player-season to the comparison. */
export function PlayerPicker({ onPick, exclude }: { onPick: (r: SearchResult) => void; exclude: Set<string> }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      searchPlayers({ q: query }, controller.signal)
        .then((data) => setResults(data.results.slice(0, 8)))
        .catch(() => undefined);
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  return (
    <div className="picker">
      <input
        type="search"
        placeholder="Add a player…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Add a player to the comparison"
      />
      {results.length > 0 && (
        <ul className="picker-results" role="listbox">
          {results.map((r) => {
            const ref = `${r.player_id}:${r.season_id}`;
            const taken = exclude.has(ref);
            return (
              <li key={ref}>
                <button
                  type="button"
                  disabled={taken}
                  onClick={() => {
                    onPick(r);
                    setQuery("");
                  }}
                >
                  <b>{r.player_name}</b>
                  <span className="muted">
                    {r.teams.join(" / ")} · {r.competition} · {r.primary_role ? ROLE_LABELS[r.primary_role] : "—"} ·{" "}
                    {formatMinutes(r.minutes)} min
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
