import { useEffect, useState } from "react";
import { fetchTeamCorners, type CornerReport, type CornerSummary } from "../api";

// Attacking end, goal at the top, taker on the left (corners mirrored, Phase 11.6). Canonical metres.
const SCALE = 5;
const X0 = 78; // show from 27 m out
const sx = (y: number) => (68 - y) * SCALE;
const sy = (x: number) => (105 - x) * SCALE;
type Rect = [number, number, number, number]; // x0, x1, y0, y1 (canonical, after mirroring: near side = y > 34)
const ZONES: Record<string, Rect> = {
  six_yard_near: [99.5, 105, 34, 43.16],
  six_yard_far: [99.5, 105, 24.84, 34],
  penalty_spot: [88.5, 99.5, 24.84, 43.16],
  box_near_side: [88.5, 105, 43.16, 54.16],
  box_far_side: [88.5, 105, 13.84, 24.84],
};

function fmt(v: number | null, digits = 3) {
  return v === null ? "—" : v.toFixed(digits);
}
function pct(v: number | null) {
  return v === null ? "—" : `${Math.round(v * 100)}%`;
}

function Delivery({ summary, title }: { summary: CornerSummary; title: string }) {
  const max = Math.max(...summary.zones.map((z) => z.share), 0.01);
  const short = summary.zones.find((z) => z.key === "short");
  return (
    <figure className="corner-map">
      <figcaption><strong>{title}</strong> <span className="muted">· {summary.corners} corners</span></figcaption>
      <svg viewBox={`-4 -4 ${68 * SCALE + 8} ${(105 - X0) * SCALE + 8}`} role="img" aria-label={`${title}: delivery zones`}>
        <rect className="line" x={0} y={0} width={68 * SCALE} height={(105 - X0) * SCALE} />
        {summary.zones.filter((z) => ZONES[z.key]).map((z) => {
          const [x0, x1, y0, y1] = ZONES[z.key];
          const r = { x: sx(y1), y: sy(x1), width: (y1 - y0) * SCALE, height: (x1 - x0) * SCALE };
          return (
            <g key={z.key}>
              <title>{`${z.label}: ${z.corners} corners (${pct(z.share)}), xG per corner ${fmt(z.xg_per_corner)}`}</title>
              <rect {...r} className="zone" style={{ fillOpacity: 0.06 + 0.84 * (z.share / max) }} />
              <text className="zone-label" x={r.x + r.width / 2} y={r.y + r.height / 2 + 4} textAnchor="middle">{pct(z.share)}</text>
            </g>
          );
        })}
        <rect className="line" x={sx(43.16)} y={0} width={18.32 * SCALE} height={5.5 * SCALE} />
        <rect className="line" x={sx(54.16)} y={0} width={40.32 * SCALE} height={16.5 * SCALE} />
        <line className="goal" x1={sx(37.66)} x2={sx(30.34)} y1={0} y2={0} />
        <circle cx={-2} cy={-2} r={5} className="taker" />
        <text className="taker-label" x={8} y={12}>taker</text>
      </svg>
      {short && <div className="muted">Short or outside the box: {pct(short.share)}</div>}
    </figure>
  );
}

/** Team corner analysis: delivery zones and what corners produce, for and against (Phase 11.6). */
export function CornersPanel({ teamId, seasonId }: { teamId: string; seasonId: string }) {
  const [report, setReport] = useState<CornerReport | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setReport(null);
    fetchTeamCorners(teamId, seasonId, controller.signal).then(setReport).catch(() => undefined);
    return () => controller.abort();
  }, [teamId, seasonId]);
  if (!report || report.for.corners === 0) return null;
  const rows: { label: string; get: (s: CornerSummary) => string }[] = [
    { label: "Corners per match", get: (s) => fmt(s.per_match, 1) },
    { label: "xG per corner", get: (s) => fmt(s.xg_per_corner) },
    { label: "Shot within the possession", get: (s) => pct(s.shot_rate) },
    { label: "Goals", get: (s) => (s.goals === null ? "—" : `${s.goals}`) },
  ];
  return (
    <section className="card" style={{ marginTop: 18 }}>
      <h2 className="section-title">Corners</h2>
      <p className="theme-note">{report.notes.zones} {report.notes.outcome}</p>
      <div className="corners-body">
        <Delivery summary={report.for} title="Corners taken" />
        <div>
          <table className="table compact">
            <thead><tr><th /><th className="num">Taken</th><th className="num">Conceded</th><th className="num">League (per team)</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td className="num">{r.get(report.for)}</td>
                  <td className="num">{r.get(report.against)}</td>
                  <td className="num muted">{r.label === "Goals" ? "—" : r.get(report.league)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="table compact" style={{ marginTop: 12 }}>
            <thead><tr><th>Delivery zone (taken)</th><th className="num">Corners</th><th className="num">Share</th><th className="num">xG / corner</th><th className="num">League xG / corner</th></tr></thead>
            <tbody>
              {report.for.zones.map((z, i) => (
                <tr key={z.key}>
                  <td>{z.label}</td>
                  <td className="num">{z.corners}</td>
                  <td className="num">{pct(z.share)}</td>
                  <td className="num">{fmt(z.xg_per_corner)}</td>
                  <td className="num muted">{fmt(report.league.zones[i].xg_per_corner)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="theme-note">xG per corner rests on few corners in some zones: read it together with the count.</p>
        </div>
      </div>
    </section>
  );
}
