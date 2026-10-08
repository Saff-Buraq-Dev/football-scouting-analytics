import type { ShotZone, ShotZonesView } from "../api";

// Canonical metres (attacking towards x = 105, goal centre y = 34). Drawn as a vertical
// half-pitch with the goal at the top. Must match analytics/shot_zones.py.
const HALF = 52.5;
const WIDTH_M = 68;
const BOX_X = 88.5;
const SIX_X = 99.5;
const EDGE_X = 80;
const GOAL_HALF = 9.16;
const BOX_HALF = 20.16;

type Rect = [x0: number, x1: number, y0: number, y1: number]; // canonical x range, y range

const ZONE_RECTS: Record<string, Rect[]> = {
  six_yard: [[SIX_X, 105, 34 - GOAL_HALF, 34 + GOAL_HALF]],
  box_central: [[BOX_X, SIX_X, 34 - GOAL_HALF, 34 + GOAL_HALF]],
  box_wide: [[BOX_X, 105, 34 - BOX_HALF, 34 - GOAL_HALF], [BOX_X, 105, 34 + GOAL_HALF, 34 + BOX_HALF]],
  edge: [[EDGE_X, BOX_X, 34 - BOX_HALF, 34 + BOX_HALF]],
  outside_wide: [[EDGE_X, 105, 0, 34 - BOX_HALF], [EDGE_X, 105, 34 + BOX_HALF, WIDTH_M]],
  long_range: [[HALF, EDGE_X, 0, WIDTH_M]],
};

const SCALE = 6; // px per metre
// Canonical y = 68 is the attacking team's LEFT touchline (docs/ARCHITECTURE.md §4.2): with the goal at the
// top of the drawing, the attacker's left must be on the left of the screen.
const svgX = (y: number) => (WIDTH_M - y) * SCALE;
const svgY = (x: number) => (105 - x) * SCALE;

function zoneRects(key: string) {
  return ZONE_RECTS[key].map(([x0, x1, y0, y1]) => ({
    x: svgX(y1), y: svgY(x1), width: (y1 - y0) * SCALE, height: (x1 - x0) * SCALE,
  }));
}

function labelPosition(key: string): { x: number; y: number } {
  const [x0, x1, y0, y1] = ZONE_RECTS[key][0];
  if (key === "box_wide" || key === "outside_wide") return { x: svgX((y0 + y1) / 2), y: svgY((x0 + x1) / 2) };
  return { x: svgX((y0 + y1) / 2), y: svgY((x0 + x1) / 2) };
}

function deltaText(zone: ShotZone): string {
  const points = Math.round((zone.share - zone.baseline_share) * 100);
  return `${points >= 0 ? "+" : ""}${points} pts`;
}

interface Props {
  title: string;
  view: ShotZonesView;
  baselineLabel: string;
}

/** Shot zones shaded by share of shots (single hue, opacity = magnitude), with a table equivalent. */
export function ShotZoneMap({ title, view, baselineLabel }: Props) {
  return (
    <section className="card shotmap">
      <h2 className="section-title">{title}</h2>
      <p className="theme-note">
        {view.totals.shots} non-penalty shots · {view.totals.goals} goals · {view.totals.npxg.toFixed(1)} npxG
        {view.penalties.taken > 0 && ` · penalties ${view.penalties.scored}/${view.penalties.taken}`}. Shade = share of
        shots; aggregated by zone (individual shots are not shown).
      </p>
      <div className="shotmap-body">
        <ShotZonePitch title={title} view={view} baselineLabel={baselineLabel} />
        <table className="table compact">
          <thead>
            <tr><th>Zone</th><th className="num">Shots</th><th className="num">Goals</th><th className="num">npxG/shot</th><th className="num">Share</th><th className="num">vs {baselineLabel}</th></tr>
          </thead>
          <tbody>
            {view.zones.map((z) => (
              <tr key={z.key}>
                <td>{z.label}</td>
                <td className="num">{z.shots}</td>
                <td className="num">{z.goals}</td>
                <td className="num">{z.npxg_per_shot === null ? "—" : z.npxg_per_shot.toFixed(2)}</td>
                <td className="num">{Math.round(z.share * 100)}%</td>
                <td className="num muted">{deltaText(z)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** The half-pitch drawing of shot zones, shared by the profile and the printable report. */
export function ShotZonePitch({ title, view, baselineLabel }: Props) {
  const maxShare = Math.max(...view.zones.map((z) => z.share), 0.01);
  return (
    <svg viewBox={`-4 -4 ${WIDTH_M * SCALE + 8} ${(105 - HALF) * SCALE + 8}`} role="img"
      aria-label={`${title}: share of shots by zone`}>
      {view.zones.map((zone) => (
        <g key={zone.key}>
          <title>{`${zone.label}: ${zone.shots} shots, ${zone.goals} goals, ${Math.round(zone.share * 100)}% of shots (${baselineLabel}: ${Math.round(zone.baseline_share * 100)}%)`}</title>
          {zoneRects(zone.key).map((r, i) => (
            <rect key={i} {...r} className="zone" style={{ fillOpacity: 0.06 + 0.84 * (zone.share / maxShare) }} />
          ))}
        </g>
      ))}
      {/* Pitch markings on top of the fills */}
      <rect className="line" x={0} y={0} width={WIDTH_M * SCALE} height={(105 - HALF) * SCALE} />
      <rect className="line" x={svgX(34 + BOX_HALF)} y={0} width={2 * BOX_HALF * SCALE} height={(105 - BOX_X) * SCALE} />
      <rect className="line" x={svgX(34 + GOAL_HALF)} y={0} width={2 * GOAL_HALF * SCALE} height={(105 - SIX_X) * SCALE} />
      <line className="goal" x1={svgX(34 + 3.66)} x2={svgX(34 - 3.66)} y1={0} y2={0} />
      {view.zones.filter((z) => z.shots > 0 && z.key !== "outside_wide").map((zone) => {
        const p = labelPosition(zone.key);
        return (
          <text key={zone.key} className="zone-label" x={p.x} y={p.y} textAnchor="middle">
            <tspan x={p.x} dy="-0.2em">{Math.round(zone.share * 100)}%</tspan>
            <tspan x={p.x} dy="1.2em" className="zone-sub">{zone.goals}/{zone.shots}</tspan>
          </text>
        );
      })}
    </svg>
  );
}
