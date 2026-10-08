import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchPlayerArchetype, fetchPlayerShots, fetchPlayerZones, fetchProfile, fetchSimilar,
  type HighlightMetric, type PlayerArchetype, type Profile, type ReportHighlights, type ShotZonesView, type SimilarityResponse,
  type ZoneMapsResponse,
} from "../api";
import { useBoardApi } from "../auth/useBoard";
import type { PlayerBoard } from "../board";
import { DataAttribution } from "../components/DataAttribution";
import { PercentileBar } from "../components/PercentileBar";
import { ShotZonePitch } from "../components/ShotZoneMap";
import { ZonePitch } from "../components/ZoneGrid";
import {
  POSITION_GROUP_PLURALS, ROLE_LABELS, formatMinutes, formatPercentile, formatShare, formatValue, inSentence,
} from "../format";

const SIMILAR_SHOWN = 5;
// Scout notes on the printed page: the most recent ones, shortened, so the report stays on one A4 page.
const NOTES_SHOWN = 3;
const NOTE_CHARS = 220;

interface Extras {
  archetype: PlayerArchetype | null;
  zones: ZoneMapsResponse | null;
  shots: (ShotZonesView & { baseline: string }) | null;
  similar: SimilarityResponse | null;
}

/** Settle a request to null: every section except the profile is optional on the report. */
const optional = <T,>(p: Promise<T>) => p.catch(() => null);

/**
 * One-page scouting report (Phase 11.8, D031), laid out for A4 portrait. The PDF is produced by the browser's
 * print dialog ("Save as PDF"); the print stylesheet hides the app shell and forces the light theme.
 */
export function ReportPage() {
  const { playerId = "", seasonId = "" } = useParams();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [extras, setExtras] = useState<Extras | null>(null);
  const [error, setError] = useState<string | null>(null);
  const boardApi = useBoardApi();
  const [board, setBoard] = useState<PlayerBoard | null>(null);

  useEffect(() => {
    setBoard(null);
    boardApi?.playerBoard(playerId).then(setBoard).catch(() => undefined);
  }, [boardApi, playerId]);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    setProfile(null);
    setExtras(null);
    fetchProfile(playerId, seasonId, signal)
      .then(setProfile)
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message === "not_found" ? "No profile for this player-season." : e.message);
      });
    Promise.all([
      optional(fetchPlayerArchetype(playerId, seasonId, signal)),
      optional(fetchPlayerZones(playerId, seasonId, signal)),
      optional(fetchPlayerShots(playerId, seasonId, signal)),
      optional(fetchSimilar(playerId, seasonId, signal)),
    ]).then(([archetype, zones, shots, similar]) => {
      if (!signal.aborted) setExtras({ archetype, zones, shots, similar });
    });
    return () => controller.abort();
  }, [playerId, seasonId]);

  useEffect(() => {
    if (!profile) return;
    const previous = document.title;
    // The browser uses the document title as the default PDF file name.
    document.title = `Scouting report - ${profile.player.name} - ${profile.season.competition} ${profile.season.label}`;
    const light = () => document.documentElement.setAttribute("data-theme", "light");
    const restore = () => document.documentElement.removeAttribute("data-theme");
    window.addEventListener("beforeprint", light);
    window.addEventListener("afterprint", restore);
    return () => {
      document.title = previous;
      window.removeEventListener("beforeprint", light);
      window.removeEventListener("afterprint", restore);
    };
  }, [profile]);

  if (error) return <div className="card empty">{error}</div>;
  if (!profile) return <div className="card empty">Loading report…</div>;

  const { playing_time: pt, population, context } = profile;
  const plural = pt.position_group ? POSITION_GROUP_PLURALS[pt.position_group] : "players";
  const populationLabel = `${population.size ?? "—"} ${plural} (≥ ${population.min_minutes} min)`;
  const touches = extras?.zones?.maps.find((m) => m.key === "touches");
  const shots = extras?.shots && extras.shots.totals.shots > 0 ? extras.shots : null;
  const generated = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

  return (
    <>
      <div className="profile-actions no-print">
        <Link className="back" to={`/players/${playerId}/seasons/${seasonId}`}>← Profile</Link>
        <span className="report-actions">
          <span className="muted">Choose “Save as PDF” in the print dialog.</span>
          <button className="button" disabled={!extras} onClick={() => window.print()}>
            {extras ? "Download PDF" : "Preparing…"}
          </button>
        </span>
      </div>

      <article className="report" aria-label="Scouting report">
        <header className="report-head">
          <div>
            <div className="eyebrow">Scouting report · {profile.season.competition} · {profile.season.label}</div>
            <h1>{profile.player.name}</h1>
            <div className="profile-sub">
              {profile.teams.join(" / ")}
              {profile.player.nationality && <> · {profile.player.nationality}</>}
              {pt.primary_role && <> · {ROLE_LABELS[pt.primary_role]} ({formatShare(pt.primary_role_share)} of minutes)</>}
            </div>
          </div>
          <dl className="report-facts">
            <div><dt>Minutes</dt><dd>{formatMinutes(pt.minutes)}</dd></div>
            <div><dt>Apps (starts)</dt><dd>{pt.appearances} ({pt.starts})</dd></div>
            <div><dt>Team possession</dt><dd>{context.team_possession_pct === null ? "—" : `${Math.round(context.team_possession_pct)}%`}</dd></div>
          </dl>
        </header>

        {!pt.eligible && (
          <p className="notice">
            <strong>Not ranked.</strong> Below the {pt.min_minutes}-minute threshold: no percentiles, small sample.
          </p>
        )}

        {extras?.archetype && (
          <p className="report-type">
            <b>Profile type</b> (one of {extras.archetype.types_in_group} among {plural}): more{" "}
            {extras.archetype.type.more.map(inSentence).join(", ")}; less {extras.archetype.type.less.map(inSentence).join(", ")}.
            {extras.archetype.also_close_to && " Between two types."}{" "}
            <span className="muted">
              Typical: {extras.archetype.type.prototypes.filter((p) => p.player_id !== playerId).slice(0, 3).map((p) => p.name).join(", ")}.
            </span>
          </p>
        )}

        <div className="report-grid">
          <div>
            {pt.eligible && <Highlights highlights={profile.highlights} />}
            <section className="report-section">
              <h2>Percentiles <span className="muted">vs {populationLabel}</span></h2>
              {profile.themes.map((theme) => (
                <div key={theme.key} className="report-theme">
                  <h3>{theme.label}</h3>
                  {theme.metrics.map((metric) => (
                    <div className="report-metric" key={metric.key}>
                      <span className={metric.reliability_band === "low" ? "muted" : undefined}>{metric.label}</span>
                      <PercentileBar metric={metric} populationLabel={populationLabel} />
                      <span className="num">{formatValue(metric)}</span>
                      <span className="num muted">{formatPercentile(metric.percentile)}</span>
                    </div>
                  ))}
                </div>
              ))}
              <p className="report-note">
                Value per 90 (ratios as shown) · percentile · pale bar and grey label = low reliability.
                {profile.themes.some((t) => t.possession_sensitive) &&
                  " Defensive volume partly reflects team possession."}
              </p>
            </section>
          </div>

          <div>
            {touches && touches.total > 0 && extras?.zones && (
              <section className="report-section zonemaps report-pitch">
                <h2>Touches <span className="muted">{touches.total} · attacking upwards</span></h2>
                <ZonePitch map={{ ...touches, title: "Touches" }} layout={extras.zones.layout} mode="share" baselineLabel={plural} />
              </section>
            )}
            {shots && (
              <section className="report-section shotmap report-pitch">
                <h2>
                  Shots <span className="muted">{shots.totals.shots} np · {shots.totals.goals} goals · {shots.totals.npxg.toFixed(1)} npxG</span>
                </h2>
                <ShotZonePitch title="Shots" view={shots} baselineLabel={POSITION_GROUP_PLURALS[shots.baseline] ?? "group"} />
              </section>
            )}
          </div>
        </div>

        {extras?.similar && extras.similar.results.length > 0 && (
          <section className="report-section">
            <h2>Similar profiles <span className="muted">closer than x % of the group</span></h2>
            <table className="table compact">
              <tbody>
                {extras.similar.results.slice(0, SIMILAR_SHOWN).map((p) => (
                  <tr key={`${p.player_id}:${p.season_id}`}>
                    <td>{p.player_name}</td>
                    <td className="muted">{p.teams.join(" / ")} · {p.competition}</td>
                    <td className="num">{Math.round(p.similarity_percentile)}%</td>
                    <td className="muted">{p.main_differences.map((d) => `${d.direction} ${inSentence(d.label)}`).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {board && <ScoutNotes board={board} seasonId={seasonId} />}

        <footer className="report-foot">
          <p>
            Percentiles: one season within the position group, 4 leagues 2015/16; not a quality rating. Highlights
            use metrics of at least medium reliability. Method: docs/FOOTBALL_ANALYTICS.md · Generated {generated}.
          </p>
          <DataAttribution />
        </footer>
      </article>
    </>
  );
}

function Highlights({ highlights }: { highlights: ReportHighlights }) {
  const list = (metrics: HighlightMetric[]) => (
    <ul>{metrics.map((m) => <li key={m.key}>{m.label} <b>{formatPercentile(m.percentile)}</b></li>)}</ul>
  );
  if (highlights.ranked.length === 0) return null;
  return (
    <section className="report-section report-highlights">
      {highlights.split ? (
        <>
          <div><h2>Highest percentiles</h2>{list(highlights.highest)}</div>
          <div><h2>Lowest percentiles</h2>{list(highlights.lowest)}</div>
        </>
      ) : (
        <div className="wide"><h2>Percentiles, highest first</h2>{list(highlights.ranked)}</div>
      )}
      {highlights.low_reliability.length > 0 && (
        <p className="report-note wide">Left out (low reliability): {highlights.low_reliability.map(inSentence).join(", ")}.</p>
      )}
    </section>
  );
}

function ScoutNotes({ board, seasonId }: { board: PlayerBoard; seasonId: string }) {
  // Notes about this season, or about the player in general.
  const notes = board.notes.filter((n) => n.season_id === null || n.season_id === seasonId);
  if (notes.length === 0 && board.tags.length === 0) return null;
  const shorten = (text: string) => (text.length > NOTE_CHARS ? `${text.slice(0, NOTE_CHARS - 1)}…` : text);
  return (
    <section className="report-section report-notes">
      <h2>Scout notes {board.tags.length > 0 && <span className="muted">tags: {board.tags.join(", ")}</span>}</h2>
      {notes.slice(0, NOTES_SHOWN).map((n) => (
        <p key={n.id}>
          <span className="muted">{new Date(n.created_at).toLocaleDateString("en-GB")}:</span> {shorten(n.body)}
        </p>
      ))}
      {notes.length > NOTES_SHOWN && <p className="muted">{notes.length - NOTES_SHOWN} older notes not shown.</p>}
      <p className="report-note">Notes are the author's opinion, not derived from the data.</p>
    </section>
  );
}
