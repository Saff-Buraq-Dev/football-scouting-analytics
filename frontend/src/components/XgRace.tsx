import { useState } from "react";
import type { MatchReport } from "../api";

const W = 640;
const H = 260;
const M = { top: 16, right: 110, bottom: 34, left: 40 };

/** Cumulative xG per 5-minute bin for both teams (step lines), goals as dots, crosshair readout. */
export function XgRace({ report }: { report: MatchReport }) {
  const [hover, setHover] = useState<number | null>(null);
  const race = report.xg_race;
  const points = [{ minute: 0, home_xg: 0, away_xg: 0, home_goals: 0, away_goals: 0 }, ...race];
  const maxMinute = points[points.length - 1].minute;
  const maxXg = Math.max(1, ...points.map((p) => Math.max(p.home_xg, p.away_xg)));
  const step = maxXg > 3 ? 1 : 0.5;
  const yMax = Math.ceil(maxXg / step) * step;
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const sx = (m: number) => M.left + (m / maxMinute) * innerW;
  const sy = (v: number) => M.top + innerH - (v / yMax) * innerH;
  const path = (key: "home_xg" | "away_xg") =>
    points.map((p, i) => (i === 0 ? `M${sx(p.minute)},${sy(p[key])}` : `H${sx(p.minute)}V${sy(p[key])}`)).join("");
  const goalDots = (key: "home" | "away") =>
    race.filter((b) => b[`${key}_goals`] > 0).map((b) => ({ minute: b.minute, xg: b[`${key}_xg`], goals: b[`${key}_goals`] }));
  const ticksY = Array.from({ length: Math.round(yMax / step) + 1 }, (_, i) => i * step);
  const ticksX = [0, 15, 30, 45, 60, 75, 90].filter((m) => m <= maxMinute);
  const sides = [
    { key: "home" as const, name: report.match.home_team, color: "var(--series-1)" },
    { key: "away" as const, name: report.match.away_team, color: "var(--series-2)" },
  ];
  const hovered = hover === null ? null : race[hover];

  return (
    <figure className="card xgrace">
      <figcaption>
        <h2 className="section-title">xG race</h2>
        <p className="theme-note">{report.notes.xg_race}</p>
        <div className="legend">
          {sides.map((s) => (
            <span key={s.key}><i style={{ background: s.color }} />{s.name}</span>
          ))}
        </div>
      </figcaption>
      <div className="xgrace-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Cumulative expected goals by minute for both teams"
          onMouseLeave={() => setHover(null)}
          onMouseMove={(e) => {
            const box = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
            const minute = ((e.clientX - box.left) / box.width * W - M.left) / innerW * maxMinute;
            const index = race.findIndex((b) => b.minute >= minute);
            setHover(index === -1 ? race.length - 1 : Math.max(index, 0));
          }}>
          {ticksY.map((t) => (
            <g key={`y${t}`}>
              <line className="grid" x1={M.left} x2={M.left + innerW} y1={sy(t)} y2={sy(t)} />
              <text className="tick" x={M.left - 6} y={sy(t) + 4} textAnchor="end">{t.toFixed(1)}</text>
            </g>
          ))}
          {ticksX.map((t) => (
            <text key={`x${t}`} className="tick" x={sx(t)} y={H - 12} textAnchor="middle">{t}'</text>
          ))}
          {sides.map((s) => (
            <path key={s.key} d={path(`${s.key}_xg`)} fill="none" stroke={s.color} strokeWidth={2} />
          ))}
          {sides.flatMap((s) => goalDots(s.key).map((g) => (
            <circle key={`${s.key}${g.minute}`} cx={sx(g.minute)} cy={sy(g.xg)} r={5} fill={s.color}
              stroke="var(--surface-1)" strokeWidth={2} />
          )))}
          {sides.map((s) => {
            const last = points[points.length - 1][`${s.key}_xg`];
            return (
              <text key={`end${s.key}`} className="end-label" x={M.left + innerW + 8} y={sy(last) + 4}>
                {s.name.split(" ")[0]} {last.toFixed(2)}
              </text>
            );
          })}
          {hovered && <line className="crosshair" x1={sx(hovered.minute)} x2={sx(hovered.minute)} y1={M.top} y2={M.top + innerH} />}
        </svg>
        {hovered && (
          <div className="xgrace-tip" style={{ left: `${(sx(hovered.minute) / W) * 100}%` }}>
            <strong>up to {Math.round(hovered.minute)}'</strong>
            {sides.map((s) => (
              <span key={s.key}><i style={{ background: s.color }} />{hovered[`${s.key}_xg`].toFixed(2)} xG
                {hovered[`${s.key}_goals`] > 0 && ` · ${hovered[`${s.key}_goals`]} goal${hovered[`${s.key}_goals`] > 1 ? "s" : ""} in this bin`}</span>
            ))}
          </div>
        )}
      </div>
    </figure>
  );
}
