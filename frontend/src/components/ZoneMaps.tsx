import { useEffect, useState } from "react";
import { fetchPlayerZones, type ZoneMapsResponse } from "../api";
import { POSITION_GROUP_PLURALS } from "../format";
import { ZoneGrid } from "./ZoneGrid";

const TITLES = { touches: "Touches", receptions: "Receptions", progression: "Progression" } as const;

/** Player touch, reception and progression zone maps (Phase 11.2). */
export function ZoneMaps({ playerId, seasonId }: { playerId: string; seasonId: string }) {
  const [data, setData] = useState<ZoneMapsResponse | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    fetchPlayerZones(playerId, seasonId, controller.signal).then(setData).catch(() => undefined);
    return () => controller.abort();
  }, [playerId, seasonId]);
  if (!data || data.maps.every((m) => m.total === 0)) return null;
  const plural = data.position_group ? POSITION_GROUP_PLURALS[data.position_group] : "players";
  return (
    <ZoneGrid
      heading="Where he plays"
      maps={data.maps.map((m) => ({ ...m, title: TITLES[m.key] }))}
      layout={data.layout}
      baselineLabel={plural}
      baselineSingular={plural.replace(/s$/, "")}
    />
  );
}
