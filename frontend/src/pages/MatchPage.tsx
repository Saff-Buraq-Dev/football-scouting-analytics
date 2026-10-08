import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchMatchReport, type MatchReport, type MatchTeamView } from "../api";
import { PassingNetwork } from "../components/PassingNetwork";
import { XgRace } from "../components/XgRace";

const ROWS: { key: keyof MatchTeamView; label: string; format: (v: number) => string; note?: string }[] = [
  { key: "xg", label: "xG", format: (v) => v.toFixed(2) },
  { key: "xpts", label: "Expected points", format: (v) => v.toFixed(2) },
  { key: "np_shots", label: "Non-penalty shots", format: (v) => `${v}` },
  { key: "possession_pct", label: "Possession", format: (v) => `${Math.round(v)}%` },
  { key: "passes", label: "Passes", format: (v) => `${v}` },
  { key: "progressive_passes", label: "Progressive passes", format: (v) => `${v}` },
  { key: "xt", label: "xT from passes and carries", format: (v) => v.toFixed(2) },
  { key: "ppda", label: "PPDA", format: (v) => v.toFixed(1), note: "lower = more pressing" },
  { key: "high_ball_wins", label: "Final-third ball wins", format: (v) => `${v}` },
];

function Comparison({ report }: { report: MatchReport }) {
  return (
    <section className="card">
      <h2 className="section-title">Team comparison</h2>
      <table className="table compact match-compare">
        <thead><tr><th className="num">{report.match.home_team}</th><th /><th>{report.match.away_team}</th></tr></thead>
        <tbody>
          {ROWS.map((row) => {
            const h = report.home[row.key] as number | null;
            const a = report.away[row.key] as number | null;
            const total = (h ?? 0) + (a ?? 0);
            return (
              <tr key={row.key}>
                <td className="num"><span className="bar-left" style={{ width: `${total ? ((h ?? 0) / total) * 100 : 0}%` }} />{h === null ? "—" : row.format(h)}</td>
                <td className="center muted">{row.label}{row.note && <div className="metric-sub">{row.note}</div>}</td>
                <td><span className="bar-right" style={{ width: `${total ? ((a ?? 0) / total) * 100 : 0}%` }} />{a === null ? "—" : row.format(a)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="theme-note">{report.notes.xpts}</p>
    </section>
  );
}

export function MatchPage() {
  const { matchId = "" } = useParams();
  const [report, setReport] = useState<MatchReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setReport(null);
    fetchMatchReport(matchId, controller.signal).then(setReport)
      .catch((e: Error) => e.name !== "AbortError" && setError("Could not load this match."));
    return () => controller.abort();
  }, [matchId]);
  if (error) return <div className="card empty">{error}</div>;
  if (!report) return <div className="card empty">Loading match…</div>;
  const { match } = report;
  return (
    <>
      <Link className="back" to={`/matches?season=${match.season_id}`}>← Matches</Link>
      <section className="card match-head">
        <div className="eyebrow">{match.competition} · {match.season_label}{match.matchweek ? ` · matchweek ${match.matchweek}` : ""} · {match.match_date}</div>
        <div className="scoreline">
          <Link className="player-link" to={`/teams/${match.home_team_id}/seasons/${match.season_id}`}>{match.home_team}</Link>
          <span className="score">{match.home_score} – {match.away_score}</span>
          <Link className="player-link" to={`/teams/${match.away_team_id}/seasons/${match.season_id}`}>{match.away_team}</Link>
        </div>
        <div className="muted center">xG {report.home.xg.toFixed(2)} – {report.away.xg.toFixed(2)}{match.venue ? ` · ${match.venue}` : ""}</div>
      </section>

      <div className="themes" style={{ marginTop: 18 }}>
        <XgRace report={report} />
        <Comparison report={report} />
      </div>

      <section className="card" style={{ marginTop: 18 }}>
        <h2 className="section-title">Passing networks</h2>
        <p className="theme-note">{report.notes.network} Lines: at least 3 completed passes between two players; thicker = more passes. Node size = passes made and received.</p>
        <div className="networks">
          <PassingNetwork team={report.home} name={match.home_team} color="var(--series-1)" />
          <PassingNetwork team={report.away} name={match.away_team} color="var(--series-2)" />
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2 className="section-title">Standouts</h2>
        <p className="theme-note">Leaders per category in this match. No overall rating.</p>
        <div className="standouts">
          {report.standouts.map((c) => (
            <div key={c.key}>
              <div className="fact-label">{c.label}</div>
              <ol>
                {c.players.map((p) => (
                  <li key={p.player_id}>
                    <Link className="player-link" to={`/players/${p.player_id}/seasons/${match.season_id}`}>{p.name}</Link>
                    <span className="muted"> {p.team} · {c.key === "key_passes" || c.key === "ball_wins" ? p.value : p.value.toFixed(2)}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <h2 className="section-title">Lineups</h2>
        <div className="networks">
          {[{ t: report.home, n: match.home_team }, { t: report.away, n: match.away_team }].map(({ t, n }) => (
            <table className="table compact" key={n}>
              <thead><tr><th>{n}</th><th className="num">Min</th></tr></thead>
              <tbody>
                {t.lineup.map((p) => (
                  <tr key={p.player_id}>
                    <td>{p.shirt ?? ""} <Link className="player-link" to={`/players/${p.player_id}/seasons/${match.season_id}`}>{p.name}</Link>{!p.starter && <span className="muted"> (sub)</span>}</td>
                    <td className="num">{Math.round(p.minutes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
        </div>
      </section>
    </>
  );
}
