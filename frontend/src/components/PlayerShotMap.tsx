import { useEffect, useState } from "react";
import { fetchPlayerShots, type ShotZonesView } from "../api";
import { POSITION_GROUP_PLURALS } from "../format";
import { ShotZoneMap } from "./ShotZoneMap";

export function PlayerShotMap({ playerId, seasonId }: { playerId: string; seasonId: string }) {
  const [view, setView] = useState<(ShotZonesView & { baseline: string }) | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setView(null);
    fetchPlayerShots(playerId, seasonId, controller.signal).then(setView).catch(() => undefined);
    return () => controller.abort();
  }, [playerId, seasonId]);
  if (!view || view.totals.shots === 0) return null;
  return (
    <div style={{ marginTop: 18 }}>
      <ShotZoneMap title="Where he shoots from" view={view}
        baselineLabel={POSITION_GROUP_PLURALS[view.baseline] ?? "group"} />
    </div>
  );
}
