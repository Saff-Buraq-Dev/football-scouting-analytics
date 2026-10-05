import { useState } from "react";

export interface ScatterPoint {
  id: string;
  label: string;
  x: number;
  y: number;
  detail: string;
}

interface Axis {
  label: string;
  format: (v: number) => string;
  /** When true, lower values are drawn higher ("up = more intense / better"). */
  inverted?: boolean;
}

interface Props {
  title: string;
  subtitle: string;
  points: ScatterPoint[];
  x: Axis;
  y: Axis;
  highlightId?: string;
  /** Points labelled regardless of position (e.g. the top of the table). */
  alwaysLabel?: string[];
  onSelect?: (id: string) => void;
}

const WIDTH = 520;
const HEIGHT = 380;
const M = { top: 16, right: 18, bottom: 44, left: 52 };
const LABELLED_EXTREMES = 2; // per axis end: selective labels, every point stays reachable by tooltip

const LABEL_CHAR_WIDTH = 6; // approximate width of an 11px label character, for collision checks
const LABEL_HEIGHT = 12;

/** Round step (1, 2 or 5 x 10^n) giving about `count` intervals. */
export function niceStep(span: number, count = 5): number {
  const raw = span / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const residual = raw / magnitude;
  return (residual > 5 ? 10 : residual > 2 ? 5 : residual > 1 ? 2 : 1) * magnitude;
}

/** Domain padded and snapped to round ticks. */
export function niceScale(values: number[]): { domain: [number, number]; ticks: number[] } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const step = niceStep((max - min) * 1.1 || 1);
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let t = lo; t <= hi + step / 2; t += step) ticks.push(Number(t.toFixed(10)));
  return { domain: [lo, hi], ticks };
}

/** Single-series scatter: one hue, league-average reference lines, selective direct labels. */
export function ScatterMap({ title, subtitle, points, x, y, highlightId, alwaysLabel = [], onSelect }: Props) {
  const [hover, setHover] = useState<string | null>(null);
  if (points.length === 0) return null;

  const xScale = niceScale(points.map((p) => p.x));
  const yScale = niceScale(points.map((p) => p.y));
  const [x0, x1] = xScale.domain;
  const [y0, y1] = yScale.domain;
  const innerW = WIDTH - M.left - M.right;
  const innerH = HEIGHT - M.top - M.bottom;
  const sx = (v: number) => M.left + ((v - x0) / (x1 - x0)) * innerW;
  const syRaw = (v: number) => ((v - y0) / (y1 - y0)) * innerH;
  const sy = (v: number) => (y.inverted ? M.top + syRaw(v) : M.top + innerH - syRaw(v));
  const meanX = points.reduce((s, p) => s + p.x, 0) / points.length;
  const meanY = points.reduce((s, p) => s + p.y, 0) / points.length;

  const byX = [...points].sort((a, b) => a.x - b.x);
  const byY = [...points].sort((a, b) => a.y - b.y);
  // Label priority: hovered, highlighted, always-labelled, then extremes. A label that would
  // overlap one already placed is skipped (the point stays reachable by tooltip and table).
  const candidates = [
    hover, highlightId, ...alwaysLabel,
    ...[...byX.slice(0, LABELLED_EXTREMES), ...byX.slice(-LABELLED_EXTREMES),
      ...byY.slice(0, LABELLED_EXTREMES), ...byY.slice(-LABELLED_EXTREMES)].map((p) => p.id),
  ].filter((id): id is string => Boolean(id));
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const labelled = new Set<string>();
  for (const id of candidates) {
    if (labelled.has(id)) continue;
    const p = points.find((point) => point.id === id);
    if (!p) continue;
    const box = { x0: sx(p.x) + 8, x1: sx(p.x) + 8 + p.label.length * LABEL_CHAR_WIDTH, y0: sy(p.y) - 7 - LABEL_HEIGHT, y1: sy(p.y) - 7 };
    const collides = placed.some((b) => box.x0 < b.x1 && box.x1 > b.x0 && box.y0 < b.y1 && box.y1 > b.y0);
    if (!collides || id === hover) {
      labelled.add(id);
      placed.push(box);
    }
  }
  const hovered = points.find((p) => p.id === hover);

  return (
    <figure className="card scatter">
      <figcaption>
        <h2>{title}</h2>
        <p className="theme-note">{subtitle}</p>
      </figcaption>
      <div className="scatter-wrap">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${title}: ${x.label} against ${y.label}`}>
          {xScale.ticks.map((t) => (
            <g key={`x${t}`}>
              <line className="grid" x1={sx(t)} x2={sx(t)} y1={M.top} y2={M.top + innerH} />
              <text className="tick" x={sx(t)} y={M.top + innerH + 16} textAnchor="middle">{x.format(t)}</text>
            </g>
          ))}
          {yScale.ticks.map((t) => (
            <g key={`y${t}`}>
              <line className="grid" x1={M.left} x2={M.left + innerW} y1={sy(t)} y2={sy(t)} />
              <text className="tick" x={M.left - 8} y={sy(t) + 4} textAnchor="end">{y.format(t)}</text>
            </g>
          ))}
          <line className="mean" x1={sx(meanX)} x2={sx(meanX)} y1={M.top} y2={M.top + innerH} />
          <line className="mean" x1={M.left} x2={M.left + innerW} y1={sy(meanY)} y2={sy(meanY)} />
          <text className="axis-label" x={M.left + innerW / 2} y={HEIGHT - 6} textAnchor="middle">{x.label} →</text>
          <text className="axis-label" transform={`translate(14 ${M.top + innerH / 2}) rotate(-90)`} textAnchor="middle">
            {y.label} →
          </text>
          {points.map((p) => (
            <g
              key={p.id}
              className={`dot${p.id === highlightId ? " highlight" : ""}`}
              tabIndex={0}
              role="button"
              aria-label={`${p.label}: ${p.detail}`}
              onMouseEnter={() => setHover(p.id)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(p.id)}
              onBlur={() => setHover(null)}
              onClick={() => onSelect?.(p.id)}
              onKeyDown={(e) => e.key === "Enter" && onSelect?.(p.id)}
            >
              <circle className="hit" cx={sx(p.x)} cy={sy(p.y)} r={12} />
              <circle className="mark" cx={sx(p.x)} cy={sy(p.y)} r={p.id === highlightId ? 6.5 : 5} />
              {labelled.has(p.id) && (
                <text className="dot-label" x={sx(p.x) + 8} y={sy(p.y) - 7}>{p.label}</text>
              )}
            </g>
          ))}
        </svg>
        {hovered && (
          <div className="scatter-tip" style={{ left: `${(sx(hovered.x) / WIDTH) * 100}%`, top: `${(sy(hovered.y) / HEIGHT) * 100}%` }}>
            <strong>{hovered.label}</strong>
            <span>{hovered.detail}</span>
          </div>
        )}
      </div>
      <p className="theme-note">Dashed lines: league average. Hover or focus a dot for details; click to open the team.</p>
    </figure>
  );
}
