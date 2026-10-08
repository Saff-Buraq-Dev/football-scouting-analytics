import { useState } from "react";
import type { ZoneCell } from "../api";

const PITCH_LENGTH = 105;
const PITCH_WIDTH = 68;
const SCALE = 4.2; // px per metre
const CHANNEL_LABELS: Record<string, string> = {
  left_wing: "left wing", left_half_space: "left half-space", centre: "centre",
  right_half_space: "right half-space", right_wing: "right wing",
};
const LABEL_MIN_SHARE = 0.02; // labels on zones with at least 2 % of actions (or a 1-point difference)

export type ZoneMode = "share" | "difference";

export interface ZoneGridMap {
  key: string;
  title: string;
  description: string;
  total: number;
  zones: ZoneCell[];
}

export type ZoneLayout = { strip_edges: number[]; channel_edges: number[]; channels: string[] };

interface Props {
  heading: string;
  maps: ZoneGridMap[];
  layout: ZoneLayout;
  /** Plural noun for the comparison population, e.g. "full-backs" or "league teams". */
  baselineLabel: string;
  /** Singular noun for the legend, e.g. "full-back" or "league team". */
  baselineSingular: string;
}

/**
 * Vertical full pitch, attacking upwards. Canonical y = 68 is the attacker's left, drawn on the left
 * (docs/ARCHITECTURE.md §4.2). Share: one hue, opacity = magnitude. Difference: diverging blue (above the
 * baseline) / red (below), neutral when equal.
 */
export function ZoneGrid({ heading, maps, layout, baselineLabel, baselineSingular }: Props) {
  const [active, setActive] = useState(maps[0]?.key);
  const [mode, setMode] = useState<ZoneMode>("share");
  const map = maps.find((m) => m.key === active) ?? maps[0];
  if (!map) return null;

  const channelNames = layout.channels;

  return (
    <section className="card zonemaps" style={{ marginTop: 18 }}>
      <div className="zonemaps-head">
        <div>
          <h2 className="section-title">{heading}</h2>
          <p className="theme-note">{map.description} · {map.total} actions · attacking upwards</p>
        </div>
        {maps.length > 1 && (
          <div className="segmented" role="tablist" aria-label="Map">
            {maps.map((m) => (
              <button key={m.key} role="tab" aria-selected={m.key === map.key} className={m.key === map.key ? "on" : ""}
                onClick={() => setActive(m.key)}>{m.title}</button>
            ))}
          </div>
        )}
        <div className="segmented" role="radiogroup" aria-label="Colour by">
          <button role="radio" aria-checked={mode === "share"} className={mode === "share" ? "on" : ""} onClick={() => setMode("share")}>Share</button>
          <button role="radio" aria-checked={mode === "difference"} className={mode === "difference" ? "on" : ""} onClick={() => setMode("difference")}>vs {baselineLabel}</button>
        </div>
      </div>
      <div className="zonemaps-body">
        <ZonePitch map={map} layout={layout} mode={mode} baselineLabel={baselineLabel} />
        <div className="zonemaps-legend">
          {mode === "share" ? (
            <p>Darker = larger share of {map.title.toLowerCase()}. Labels on zones with at least 2 %.</p>
          ) : (
            <p>
              <span className="swatch" style={{ background: "var(--accent)" }} /> more than the average {baselineSingular}{" "}
              <span className="swatch" style={{ background: "var(--diverging-negative)" }} /> less. Labels in percentage points.
            </p>
          )}
          <p className="muted">Zones: 6 strips × 5 channels (wings, half-spaces, centre) bounded by the box and six-yard-box lines. Aggregated; individual actions are not shown.</p>
          <details>
            <summary>Share by channel</summary>
            <table className="table compact">
              <tbody>
                {[...channelNames].reverse().map((channel) => {
                  const zones = map.zones.filter((z) => z.channel === channel);
                  const own = zones.reduce((s, z) => s + z.share, 0);
                  const base = zones.reduce((s, z) => s + z.group_share, 0);
                  return (
                    <tr key={channel}>
                      <td>{CHANNEL_LABELS[channel]}</td>
                      <td className="num">{Math.round(own * 100)}%</td>
                      <td className="num muted">{baselineLabel}: {Math.round(base * 100)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </details>
        </div>
      </div>
    </section>
  );
}

/** The pitch drawing of one zone map, shared by the profile and the printable report. */
export function ZonePitch({ map, layout, mode, baselineLabel }: {
  map: ZoneGridMap; layout: ZoneLayout; mode: ZoneMode; baselineLabel: string;
}) {
  const { strip_edges: strips, channel_edges: channels, channels: channelNames } = layout;
  const maxShare = Math.max(...map.zones.map((z) => z.share), 0.001);
  const maxDiff = Math.max(...map.zones.map((z) => Math.abs(z.share - z.group_share)), 0.001);
  const sx = (y: number) => (PITCH_WIDTH - y) * SCALE;
  const sy = (x: number) => (PITCH_LENGTH - x) * SCALE;
  return (
    <svg viewBox={`-6 -6 ${PITCH_WIDTH * SCALE + 12} ${PITCH_LENGTH * SCALE + 12}`} role="img"
      aria-label={`${map.title} by zone`}>
      {map.zones.map((z) => {
        const c = channelNames.indexOf(z.channel);
        const x = sx(channels[c + 1]);
        const width = (channels[c + 1] - channels[c]) * SCALE;
        const y = sy(strips[z.strip + 1]);
        const height = (strips[z.strip + 1] - strips[z.strip]) * SCALE;
        const diff = z.share - z.group_share;
        const fill = mode === "share" ? "var(--accent)" : diff >= 0 ? "var(--accent)" : "var(--diverging-negative)";
        const opacity = mode === "share" ? 0.05 + 0.85 * (z.share / maxShare) : 0.05 + 0.85 * (Math.abs(diff) / maxDiff);
        const label = mode === "share"
          ? z.share >= LABEL_MIN_SHARE ? `${Math.round(z.share * 100)}%` : ""
          : Math.abs(diff) >= 0.01 ? `${diff > 0 ? "+" : ""}${Math.round(diff * 100)}` : "";
        return (
          <g key={z.index}>
            <title>{`${CHANNEL_LABELS[z.channel]}, zone ${z.strip + 1}/6 from own goal: ${z.count} actions, ${Math.round(z.share * 100)}% (${baselineLabel}: ${Math.round(z.group_share * 100)}%)`}</title>
            <rect x={x} y={y} width={width} height={height} className="zone" style={{ fill, fillOpacity: opacity }} />
            {label && <text className="zone-label" x={x + width / 2} y={y + height / 2 + 4} textAnchor="middle">{label}</text>}
          </g>
        );
      })}
      {/* Pitch markings */}
      <rect className="line" x={0} y={0} width={PITCH_WIDTH * SCALE} height={PITCH_LENGTH * SCALE} />
      <line className="line" x1={0} x2={PITCH_WIDTH * SCALE} y1={sy(52.5)} y2={sy(52.5)} />
      <circle className="line" cx={sx(34)} cy={sy(52.5)} r={9.15 * SCALE} />
      <rect className="line" x={sx(34 + 20.16)} y={0} width={40.32 * SCALE} height={16.5 * SCALE} />
      <rect className="line" x={sx(34 + 20.16)} y={sy(16.5)} width={40.32 * SCALE} height={16.5 * SCALE} />
    </svg>
  );
}
