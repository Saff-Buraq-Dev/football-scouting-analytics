import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchProfile, type Profile } from "../api";
import { AllMetricsTable } from "../components/AllMetricsTable";
import { MetricRow, ScaleLegend } from "../components/MetricRow";
import { SimilarPlayers } from "../components/SimilarPlayers";
import { POSITION_GROUP_PLURALS, ROLE_LABELS, formatMinutes, formatShare } from "../format";

export function ProfilePage() {
  const { playerId = "", seasonId = "" } = useParams();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setProfile(null);
    fetchProfile(playerId, seasonId, controller.signal)
      .then(setProfile)
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message === "not_found" ? "No profile for this player-season." : e.message);
      });
    return () => controller.abort();
  }, [playerId, seasonId]);

  if (error) return <div className="card empty">{error}</div>;
  if (!profile) return <div className="card empty">Loading profile…</div>;

  const { playing_time: pt, population, context } = profile;
  const groupPlural = pt.position_group ? POSITION_GROUP_PLURALS[pt.position_group] : "players";
  const populationLabel = `${population.size ?? "—"} ${groupPlural} (≥ ${population.min_minutes} min, 2015/16)`;
  const possession = context.team_possession_pct;

  return (
    <>
      <div className="profile-actions">
        <Link className="back" to="/">← Search</Link>
        <Link className="button" to={`/compare?ps=${playerId}:${seasonId}`}>
          Compare with other players
        </Link>
      </div>

      <section className="card">
        <div className="profile-head">
          <div>
            <div className="eyebrow">
              {profile.season.competition} · {profile.season.label}
            </div>
            <h1>{profile.player.name}</h1>
            <div className="profile-sub">
              {profile.teams.join(" / ")}
              {profile.player.nationality && <> · {profile.player.nationality}</>}
              {pt.primary_role && (
                <>
                  {" "}· {ROLE_LABELS[pt.primary_role]} <span className="muted">({formatShare(pt.primary_role_share)} of minutes)</span>
                </>
              )}
            </div>
          </div>
          <div className="facts">
            <div>
              <div className="fact-label">Minutes</div>
              <div className="fact-value">{formatMinutes(pt.minutes)}</div>
            </div>
            <div>
              <div className="fact-label">Appearances</div>
              <div className="fact-value">{pt.appearances}</div>
            </div>
            <div>
              <div className="fact-label">Starts</div>
              <div className="fact-value">{pt.starts}</div>
            </div>
            <div>
              <div className="fact-label">Team possession</div>
              <div className="fact-value">{possession === null ? "—" : `${Math.round(possession)}%`}</div>
            </div>
          </div>
        </div>
        {!pt.eligible && (
          <div className="notice">
            <strong>Not ranked.</strong> {formatMinutes(pt.minutes)} minutes is below the {pt.min_minutes}-minute
            threshold, so per-90 values are shown without percentiles. Small samples are noisy: read the
            regressed estimates and reliability first.
          </div>
        )}
      </section>

      <div className="context">
        <span>
          Compared with <b>{populationLabel}</b> across 4 leagues
        </span>
        <span>Percentiles describe this season; they are not a quality rating.</span>
      </div>

      <div className="themes">
        {profile.themes.map((theme) => (
          <section className="card theme" key={theme.key} aria-labelledby={`theme-${theme.key}`}>
            <h2 id={`theme-${theme.key}`}>{theme.label}</h2>
            {theme.possession_sensitive && possession !== null && (
              <p className="theme-note">
                Team had {Math.round(possession)}% possession. Defensive volume partly reflects team style, not only
                the player.
              </p>
            )}
            {!theme.possession_sensitive && <p className="theme-note">&nbsp;</p>}
            <ScaleLegend />
            {theme.metrics.map((metric) => (
              <MetricRow key={metric.key} metric={metric} populationLabel={populationLabel} />
            ))}
          </section>
        ))}
      </div>

      <SimilarPlayers playerId={playerId} seasonId={seasonId} />

      <AllMetricsTable metrics={profile.all_metrics} />
    </>
  );
}
