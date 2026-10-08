import type { MatchTeamView } from "../api";

const LENGTH = 105;
const WIDTH = 68;
const SCALE = 3.4;

const lastName = (name: string) => name.split(" ").slice(-1)[0];

/** Passing network on a vertical pitch, attacking upwards; attacker's left (y = 68) on the left (§4.2). */
export function PassingNetwork({ team, name, color }: { team: MatchTeamView; name: string; color: string }) {
  const net = team.network;
  const nodes = new Map(net.nodes.map((n) => [n.player_id, n]));
  const maxInvolvement = Math.max(1, ...net.nodes.map((n) => n.involvement));
  const maxLink = Math.max(1, ...net.links.map((l) => l.passes));
  const sx = (y: number) => (WIDTH - y) * SCALE;
  const sy = (x: number) => (LENGTH - x) * SCALE;

  // Labels: most involved players first; a label overlapping one already placed is skipped
  // (the name stays available on hover).
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const labelled = new Set<string>();
  for (const n of [...net.nodes].sort((a, b) => b.involvement - a.involvement)) {
    const text = lastName(n.name);
    const cx = sx(n.y);
    const top = sy(n.x) - 15;
    const box = { x0: cx - text.length * 2.9, x1: cx + text.length * 2.9, y0: top - 10, y1: top + 2 };
    if (!placed.some((b) => box.x0 < b.x1 && box.x1 > b.x0 && box.y0 < b.y1 && box.y1 > b.y0)) {
      placed.push(box);
      labelled.add(n.player_id);
    }
  }
  return (
    <figure className="network">
      <figcaption>
        <strong>{name}</strong>
        <span className="muted"> · {net.completed_passes} completed passes until {Math.round(net.cutoff_minute)}' ({net.cutoff_reason})</span>
        {net.small_sample && <div className="notice">Small sample: fewer than 100 completed passes before the first change. Read with caution.</div>}
      </figcaption>
      <svg viewBox={`-6 -6 ${WIDTH * SCALE + 12} ${LENGTH * SCALE + 12}`} role="img" aria-label={`${name} passing network`}>
        <rect className="pitch-line" x={0} y={0} width={WIDTH * SCALE} height={LENGTH * SCALE} />
        <line className="pitch-line" x1={0} x2={WIDTH * SCALE} y1={sy(52.5)} y2={sy(52.5)} />
        <rect className="pitch-line" x={sx(54.16)} y={0} width={40.32 * SCALE} height={16.5 * SCALE} />
        <rect className="pitch-line" x={sx(54.16)} y={sy(16.5)} width={40.32 * SCALE} height={16.5 * SCALE} />
        {net.links.map((l) => {
          const a = nodes.get(l.a);
          const b = nodes.get(l.b);
          if (!a || !b) return null;
          return (
            <line key={`${l.a}${l.b}`} x1={sx(a.y)} y1={sy(a.x)} x2={sx(b.y)} y2={sy(b.x)} stroke={color}
              strokeOpacity={0.25 + 0.6 * (l.passes / maxLink)} strokeWidth={1 + 5 * (l.passes / maxLink)}>
              <title>{`${a.name} ↔ ${b.name}: ${l.passes} passes`}</title>
            </line>
          );
        })}
        {net.nodes.map((n) => (
          <g key={n.player_id}>
            <title>{`${n.name}: ${n.involvement} passes made or received`}</title>
            <circle cx={sx(n.y)} cy={sy(n.x)} r={5 + 9 * Math.sqrt(n.involvement / maxInvolvement)} fill={color}
              stroke="var(--surface-1)" strokeWidth={2} />
            {labelled.has(n.player_id) && (
              <text className="node-label" x={sx(n.y)} y={sy(n.x) - 15} textAnchor="middle">{lastName(n.name)}</text>
            )}
          </g>
        ))}
      </svg>
    </figure>
  );
}
