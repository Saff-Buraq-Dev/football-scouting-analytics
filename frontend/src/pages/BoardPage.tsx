import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useBoardApi } from "../auth/useBoard";
import type { Shortlist, ShortlistEntry } from "../board";
import { LoginPrompt } from "../components/LoginPrompt";
import { MAX_COMPARED, playerSeasonRef } from "../api";
import { POSITION_GROUP_LABELS, formatMinutes } from "../format";

/** Recruitment board (Phase 11.9, D032): the user's shortlists, with tags and note counts per player. */
export function BoardPage() {
  const { client, user } = useAuth();
  const api = useBoardApi();
  const [params, setParams] = useSearchParams();
  const [lists, setLists] = useState<Shortlist[] | null>(null);
  const [entries, setEntries] = useState<ShortlistEntry[] | null>(null);
  const [name, setName] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = params.get("list") ?? lists?.[0]?.id ?? null;
  const current = lists?.find((l) => l.id === selected) ?? null;

  const loadLists = useCallback(() => {
    api?.shortlists().then(setLists).catch((e: Error) => setError(e.message));
  }, [api]);
  useEffect(loadLists, [loadLists]);

  const loadEntries = useCallback(() => {
    setEntries(null);
    if (api && selected) api.entries(selected).then(setEntries).catch((e: Error) => setError(e.message));
  }, [api, selected]);
  useEffect(loadEntries, [loadEntries]);
  useEffect(() => setTagFilter(null), [selected]);

  if (!client) return <div className="card empty">Loading…</div>;
  if (client.mode === "disabled") {
    return (
      <div className="card empty">
        The recruitment board needs a login, which is not configured on this server (AUTH_PROVIDER, see deploy/README.md).
      </div>
    );
  }
  if (!user || !api) return <div className="card empty"><LoginPrompt what="see your shortlists" /></div>;

  const create = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    api.createShortlist(name)
      .then((l) => { setName(""); loadLists(); setParams({ list: l.id }); })
      .catch((err: Error) => setError(err.message));
  };
  const remove = (entry: ShortlistEntry) => {
    if (!selected) return;
    api.removeEntry(selected, entry.player_id, entry.season_id).then(() => { loadEntries(); loadLists(); })
      .catch((err: Error) => setError(err.message));
  };
  const deleteList = () => {
    if (!current || !window.confirm(`Delete the shortlist “${current.name}”? Tags and notes are kept.`)) return;
    api.deleteShortlist(current.id).then(() => { setParams({}); loadLists(); }).catch((err: Error) => setError(err.message));
  };

  const tags = [...new Set((entries ?? []).flatMap((e) => e.tags))].sort();
  const shown = (entries ?? []).filter((e) => !tagFilter || e.tags.includes(tagFilter));
  const compareRefs = shown.map((e) => `ps=${playerSeasonRef(e.player_id, e.season_id)}`);

  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Recruitment board</div>
        <h1>Shortlists</h1>
        <p>Your shortlists, tags and notes are private to your account. Add players from their profile page.</p>
      </div>
      {error && <p className="notice" role="alert">{error}</p>}
      <div className="board-layout">
        <aside className="card board-lists">
          {lists?.length === 0 && <p className="muted">No shortlist yet.</p>}
          <ul>
            {lists?.map((l) => (
              <li key={l.id}>
                <button className={l.id === selected ? "on" : ""} onClick={() => setParams({ list: l.id })}>
                  <span>{l.name}</span> <span className="muted">{l.size}</span>
                </button>
              </li>
            ))}
          </ul>
          <form className="inline-form" onSubmit={create}>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New shortlist" maxLength={80}
              aria-label="New shortlist name" />
            <button className="button small" type="submit" disabled={!name.trim()}>Create</button>
          </form>
        </aside>

        <section className="card" style={{ padding: 0 }}>
          {!current ? (
            <div className="empty">Create a shortlist, then add players from their profile.</div>
          ) : (
            <>
              <div className="board-list-head">
                <div>
                  <h2 className="section-title">{current.name}</h2>
                  {current.description && <p className="theme-note">{current.description}</p>}
                </div>
                <span className="report-actions">
                  {shown.length >= 2 && shown.length <= MAX_COMPARED && (
                    <Link className="button small" to={`/compare?${compareRefs.join("&")}`}>Compare these {shown.length}</Link>
                  )}
                  <button className="button small" onClick={deleteList}>Delete list</button>
                </span>
              </div>
              {tags.length > 0 && (
                <div className="chips board-filter" role="group" aria-label="Filter by tag">
                  <button className={`chip${tagFilter === null ? " on" : ""}`} onClick={() => setTagFilter(null)}>All</button>
                  {tags.map((t) => (
                    <button key={t} className={`chip${tagFilter === t ? " on" : ""}`} onClick={() => setTagFilter(t)}>{t}</button>
                  ))}
                </div>
              )}
              {entries === null ? (
                <div className="empty">Loading…</div>
              ) : shown.length === 0 ? (
                <div className="empty">No player in this shortlist yet.</div>
              ) : (
                <table className="table">
                  <thead>
                    <tr><th>Player</th><th>Position</th><th className="num">Min</th><th>Tags</th><th className="num">Notes</th><th /></tr>
                  </thead>
                  <tbody>
                    {shown.map((e) => (
                      <tr key={playerSeasonRef(e.player_id, e.season_id)}>
                        <td>
                          <Link className="player-link" to={`/players/${e.player_id}/seasons/${e.season_id}`}>{e.player_name}</Link>
                          <div className="metric-sub">{(e.teams ?? []).join(" / ")} · {e.competition} {e.season_label}</div>
                        </td>
                        <td className="secondary">{e.position_group ? POSITION_GROUP_LABELS[e.position_group] : "—"}</td>
                        <td className="num">{e.minutes === null ? "—" : formatMinutes(e.minutes)}</td>
                        <td><span className="chips">{e.tags.map((t) => <span className="chip" key={t}>{t}</span>)}</span></td>
                        <td className="num">{e.notes || ""}</td>
                        <td className="row-actions">
                          <Link className="button small" to={`/players/${e.player_id}/seasons/${e.season_id}/report`}>Report</Link>
                          <button className="link-button" onClick={() => remove(e)}>Remove</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}
