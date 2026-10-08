import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchArchetypes, type ArchetypeType } from "../api";
import { TypeDescription } from "../components/ArchetypeCard";
import { POSITION_GROUP_LABELS } from "../format";

const ORDER = ["centre_back", "full_back", "central_midfield", "attacking_midfield_winger", "striker"];

export function ArchetypesPage() {
  const [data, setData] = useState<{ groups: Record<string, ArchetypeType[]>; note: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchArchetypes(controller.signal).then(setData).catch(() => undefined);
    return () => controller.abort();
  }, []);
  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Archetypes</div>
        <h1>Player types by position</h1>
        <p>Groups of players with a similar profile shape, found by the data, described by what they do more and less than their position group.</p>
      </div>
      {data && <p className="notice">{data.note} Goalkeepers are not typed (too few comparable metrics).</p>}
      <div className="themes" style={{ marginTop: 18 }}>
        {data && ORDER.filter((g) => data.groups[g]).map((group) => (
          <section className="card" key={group}>
            <h2 className="section-title">{POSITION_GROUP_LABELS[group]}</h2>
            {data.groups[group].map((type) => (
              <div className="archetype-type" key={type.index}>
                <div><TypeDescription type={type} /> <span className="muted">· {type.size} players</span></div>
                <div className="metric-sub">
                  Typical:{" "}
                  {type.prototypes.map((p, i) => (
                    <span key={p.player_id}>
                      {i > 0 && ", "}
                      <Link className="player-link" to={`/players/${p.player_id}/seasons/${p.season_id}`}>{p.name}</Link>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </section>
        ))}
      </div>
    </>
  );
}
