import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPlayerArchetype, type ArchetypeType, type PlayerArchetype } from "../api";
import { POSITION_GROUP_PLURALS, inSentence } from "../format";

export function TypeDescription({ type }: { type: ArchetypeType }) {
  return (
    <span>
      more <b>{type.more.map(inSentence).join(", ")}</b>
      <span className="muted"> · less {type.less.map(inSentence).join(", ")}</span>
    </span>
  );
}

/** The player's archetype (Phase 11.7): computed description + typical players, no invented name. */
export function ArchetypeCard({ playerId, seasonId }: { playerId: string; seasonId: string }) {
  const [data, setData] = useState<PlayerArchetype | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    fetchPlayerArchetype(playerId, seasonId, controller.signal).then(setData).catch(() => undefined);
    return () => controller.abort();
  }, [playerId, seasonId]);
  if (!data) return null;
  const others = data.type.prototypes.filter((p) => p.player_id !== playerId).slice(0, 4);
  return (
    <section className="card archetype" style={{ marginTop: 18 }}>
      <div className="archetype-head">
        <h2 className="section-title">Profile type</h2>
        <Link className="muted" to="/archetypes">All types →</Link>
      </div>
      <p>
        One of {data.types_in_group} types among {POSITION_GROUP_PLURALS[data.position_group]}: <TypeDescription type={data.type} />.
      </p>
      <p className="secondary">
        Most typical of this type:{" "}
        {others.map((p, i) => (
          <span key={p.player_id}>
            {i > 0 && ", "}
            <Link className="player-link" to={`/players/${p.player_id}/seasons/${p.season_id}`}>{p.name}</Link>
          </span>
        ))}
      </p>
      {data.also_close_to && (
        <p className="notice">
          Between two types: also close to the type with <TypeDescription type={data.also_close_to} />.
        </p>
      )}
      <p className="theme-note">{data.note}</p>
    </section>
  );
}
