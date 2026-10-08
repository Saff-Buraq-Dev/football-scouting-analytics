import { useEffect, useState } from "react";
import { fetchTeamPressing, type PressingMapsResponse } from "../api";
import { ZoneGrid } from "./ZoneGrid";

const TITLES = { defensive_actions: "Defensive actions", ball_wins: "Ball wins" } as const;

/** Team pressing maps: where it defends and where it wins the ball back (Phase 11.3). */
export function PressingMaps({ teamId, seasonId }: { teamId: string; seasonId: string }) {
  const [data, setData] = useState<PressingMapsResponse | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    fetchTeamPressing(teamId, seasonId, controller.signal).then(setData).catch(() => undefined);
    return () => controller.abort();
  }, [teamId, seasonId]);
  if (!data) return null;
  return (
    <ZoneGrid
      heading="Where it defends and wins the ball"
      maps={data.maps.map((m) => ({ ...m, title: TITLES[m.key] }))}
      layout={data.layout}
      baselineLabel="league teams"
      baselineSingular="league team"
    />
  );
}
