import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useBoardApi } from "../auth/useBoard";
import type { PlayerBoard, Shortlist } from "../board";
import { LoginPrompt } from "./LoginPrompt";

const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });

/** The signed-in user's shortlists, tags and notes for one player (Phase 11.9). Private to that user. */
export function BoardPanel({ playerId, seasonId, seasonLabel }: { playerId: string; seasonId: string; seasonLabel: string }) {
  const { client, user } = useAuth();
  const api = useBoardApi();
  const [board, setBoard] = useState<PlayerBoard | null>(null);
  const [lists, setLists] = useState<Shortlist[]>([]);
  const [target, setTarget] = useState("");
  const [newList, setNewList] = useState("");
  const [tag, setTag] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!api) return;
    Promise.all([api.playerBoard(playerId), api.shortlists()])
      .then(([b, l]) => { setBoard(b); setLists(l); })
      .catch((e: Error) => setError(e.message));
  }, [api, playerId]);
  useEffect(reload, [reload]);

  if (!client || client.mode === "disabled") return null;
  if (!user || !api) {
    return (
      <section className="card board-panel" style={{ marginTop: 18 }}>
        <h2 className="section-title">Recruitment board</h2>
        <LoginPrompt what="shortlist, tag and annotate this player" />
      </section>
    );
  }

  const run = (action: Promise<unknown>, after?: () => void) => {
    setError(null);
    action.then(() => { after?.(); reload(); }).catch((e: Error) => setError(e.message));
  };
  const inThisSeason = new Set(board?.shortlists.filter((s) => s.season_id === seasonId).map((s) => s.shortlist_id));
  const available = lists.filter((l) => !inThisSeason.has(l.id));

  const addToList = (e: FormEvent) => {
    e.preventDefault();
    if (target) run(api.addEntry(target, playerId, seasonId), () => setTarget(""));
    else if (newList.trim()) {
      run(api.createShortlist(newList).then((l) => api.addEntry(l.id, playerId, seasonId)), () => setNewList(""));
    }
  };

  return (
    <section className="card board-panel" style={{ marginTop: 18 }}>
      <div className="archetype-head">
        <h2 className="section-title">Recruitment board</h2>
        <span className="muted">Private to you · <Link to="/board">All shortlists →</Link></span>
      </div>
      {error && <p className="notice" role="alert">{error}</p>}

      <div className="board-row">
        <span className="board-label">Shortlists</span>
        <div className="chips">
          {board?.shortlists.filter((s) => s.season_id === seasonId).map((s) => (
            <span className="chip" key={s.shortlist_id}>
              {s.name}
              <button aria-label={`Remove from ${s.name}`} onClick={() => run(api.removeEntry(s.shortlist_id, playerId, seasonId))}>×</button>
            </span>
          ))}
          <form className="inline-form" onSubmit={addToList}>
            {available.length > 0 && (
              <select value={target} onChange={(e) => setTarget(e.target.value)} aria-label="Shortlist">
                <option value="">New shortlist…</option>
                {available.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            )}
            {!target && (
              <input value={newList} onChange={(e) => setNewList(e.target.value)} placeholder="New shortlist name"
                maxLength={80} aria-label="New shortlist name" />
            )}
            <button className="button small" type="submit">Add {seasonLabel}</button>
          </form>
        </div>
      </div>

      <div className="board-row">
        <span className="board-label">Tags</span>
        <div className="chips">
          {board?.tags.map((t) => (
            <span className="chip" key={t}>
              {t}
              <button aria-label={`Remove tag ${t}`} onClick={() => run(api.removeTag(playerId, t))}>×</button>
            </span>
          ))}
          <form className="inline-form" onSubmit={(e) => { e.preventDefault(); if (tag.trim()) run(api.addTag(playerId, tag), () => setTag("")); }}>
            <input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="Add tag" maxLength={30} aria-label="Add tag" />
          </form>
        </div>
      </div>

      <div className="board-row">
        <span className="board-label">Notes</span>
        <div>
          <form className="note-form" onSubmit={(e) => { e.preventDefault(); if (note.trim()) run(api.addNote(playerId, note, seasonId), () => setNote("")); }}>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={5000}
              placeholder={`Note about this player (${seasonLabel})`} aria-label="New note" />
            <button className="button small" type="submit">Add note</button>
          </form>
          {board?.notes.map((n) => (
            <div className="note" key={n.id}>
              <p>{n.body}</p>
              <div className="metric-sub">
                {dateFormat.format(new Date(n.created_at))}{n.season_label && ` · about ${n.season_label}`}{" "}
                <button className="link-button" onClick={() => run(api.deleteNote(n.id))}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
