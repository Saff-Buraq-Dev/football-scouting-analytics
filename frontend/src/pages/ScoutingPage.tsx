import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  MAX_COMPARED,
  fetchMetricDefinitions,
  fetchPresets,
  fetchSeasons,
  playerSeasonRef,
  runScouting,
  type MetricDefinition,
  type ScoutCriterionValue,
  type ScoutingPreset,
  type ScoutingResponse,
  type Season,
} from "../api";
import { POSITION_GROUP_LABELS, POSITION_GROUP_PLURALS, formatMinutes, formatPercentile, formatValue } from "../format";

const MAX_CRITERIA = 6;
const DEBOUNCE_MS = 300;

interface CriterionInput {
  key: string;
  min_percentile: number;
}

function CriterionCell({ value }: { value: ScoutCriterionValue }) {
  return (
    <td className={`scout-cell${value.passes ? "" : " scout-miss"}`}>
      <div className="scout-cell-top">
        <span className="scout-pct">{formatPercentile(value.percentile)}</span>
        <span className="muted">{formatValue({ key: value.key, unit: "per_90", value: value.value })}</span>
      </div>
      <div className="scout-meter" aria-hidden="true">
        <div style={{ width: `${Math.max(value.percentile ?? 0, 1.5)}%` }} />
      </div>
    </td>
  );
}

export function ScoutingPage() {
  const navigate = useNavigate();
  const [presets, setPresets] = useState<ScoutingPreset[]>([]);
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [group, setGroup] = useState("central_midfield");
  const [criteria, setCriteria] = useState<CriterionInput[]>([]);
  const [seasonId, setSeasonId] = useState("");
  const [minPossession, setMinPossession] = useState("");
  const [maxPossession, setMaxPossession] = useState("");
  const [result, setResult] = useState<ScoutingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchPresets(controller.signal), fetchMetricDefinitions(controller.signal), fetchSeasons(controller.signal)])
      .then(([p, m, s]) => {
        setPresets(p);
        setMetrics(m);
        setSeasons(s.filter((season) => season.player_count > 0));
        const first = p.find((preset) => preset.position_group === "central_midfield");
        if (first) setCriteria(first.criteria.map(({ key, min_percentile }) => ({ key, min_percentile })));
      })
      .catch(() => setError("Could not reach the API. Is it running on port 8000?"));
    return () => controller.abort();
  }, []);

  const groupMetrics = useMemo(
    () => metrics.filter((m) => m.position_groups === null || m.position_groups.includes(group)),
    [metrics, group],
  );
  const groupPresets = presets.filter((p) => p.position_group === group);

  useEffect(() => {
    if (criteria.length === 0) {
      setResult(null);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      runScouting(
        {
          position_group: group,
          criteria,
          season_id: seasonId || undefined,
          min_possession: minPossession === "" ? undefined : Number(minPossession),
          max_possession: maxPossession === "" ? undefined : Number(maxPossession),
        },
        controller.signal,
      )
        .then((r) => {
          setResult(r);
          setError(null);
        })
        .catch((e: Error) => {
          if (e.name !== "AbortError") setError("The search could not run. Check the criteria.");
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [group, criteria, seasonId, minPossession, maxPossession]);

  const applyPreset = (key: string) => {
    const preset = presets.find((p) => p.key === key);
    if (preset) setCriteria(preset.criteria.map(({ key: k, min_percentile }) => ({ key: k, min_percentile })));
  };

  const changeGroup = (next: string) => {
    setGroup(next);
    setSelected([]);
    const preset = presets.find((p) => p.position_group === next);
    setCriteria(preset ? preset.criteria.map(({ key, min_percentile }) => ({ key, min_percentile })) : []);
  };

  const updateCriterion = (index: number, patch: Partial<CriterionInput>) =>
    setCriteria(criteria.map((c, i) => (i === index ? { ...c, ...patch } : c)));

  const addCriterion = () => {
    const unused = groupMetrics.find((m) => !criteria.some((c) => c.key === m.key));
    if (unused) setCriteria([...criteria, { key: unused.key, min_percentile: 60 }]);
  };

  const toggle = (ref: string) =>
    setSelected((current) =>
      current.includes(ref) ? current.filter((r) => r !== ref) : current.length < MAX_COMPARED ? [...current, ref] : current,
    );

  const labelOf = (key: string) => metrics.find((m) => m.key === key)?.label ?? key;

  return (
    <>
      <div className="search-head">
        <div className="eyebrow">Scouting</div>
        <h1>Screen a position group</h1>
        <p>
          Players must meet every criterion (percentile within their position group). They are then ordered without a
          weighted score: tier 1 means no other candidate is better on every criterion.
        </p>
      </div>

      <section className="card scout-form">
        <div className="scout-row">
          <label>
            <span className="fact-label">Position group</span>
            <select value={group} onChange={(e) => changeGroup(e.target.value)}>
              {Object.entries(POSITION_GROUP_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="fact-label">Role preset</span>
            <select value="" onChange={(e) => applyPreset(e.target.value)}>
              <option value="">Apply a preset…</option>
              {groupPresets.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}: {p.intent.toLowerCase()}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="fact-label">Competition</span>
            <select value={seasonId} onChange={(e) => setSeasonId(e.target.value)}>
              <option value="">All four leagues</option>
              {seasons.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.competition} {s.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="fact-label">Team possession %</span>
            <span className="scout-range">
              <input type="number" min={0} max={100} placeholder="min" value={minPossession}
                onChange={(e) => setMinPossession(e.target.value)} aria-label="Minimum team possession" />
              <span className="muted">to</span>
              <input type="number" min={0} max={100} placeholder="max" value={maxPossession}
                onChange={(e) => setMaxPossession(e.target.value)} aria-label="Maximum team possession" />
            </span>
          </label>
        </div>

        <div className="fact-label" style={{ marginTop: 16 }}>Criteria (minimum percentile)</div>
        <div className="scout-criteria">
          {criteria.map((c, i) => (
            <div className="scout-criterion" key={i}>
              <select value={c.key} onChange={(e) => updateCriterion(i, { key: e.target.value })} aria-label="Metric">
                {groupMetrics.map((m) => (
                  <option key={m.key} value={m.key} disabled={m.key !== c.key && criteria.some((o) => o.key === m.key)}>
                    {m.label}
                  </option>
                ))}
              </select>
              <span className="muted">≥</span>
              <input type="number" min={0} max={100} step={5} value={c.min_percentile}
                onChange={(e) => updateCriterion(i, { min_percentile: Math.min(100, Math.max(0, Number(e.target.value))) })}
                aria-label="Minimum percentile" />
              <button type="button" className="remove" aria-label="Remove criterion"
                onClick={() => setCriteria(criteria.filter((_, j) => j !== i))}>×</button>
            </div>
          ))}
          {criteria.length < MAX_CRITERIA && (
            <button type="button" className="button" onClick={addCriterion}>+ Add criterion</button>
          )}
        </div>
      </section>

      {error && <div className="card empty">{error}</div>}

      {result && (
        <>
          <div className="context">
            <span>
              <b>{result.shortlisted}</b> of {result.population_size} ranked {POSITION_GROUP_PLURALS[group]} meet every
              criterion · <b>{result.tier_1}</b> in tier 1
            </span>
            {selected.length > 0 && (
              <button type="button" className="button"
                onClick={() => navigate(`/compare?${selected.map((s) => `ps=${s}`).join("&")}`)}>
                Compare selected ({selected.length})
              </button>
            )}
          </div>

          <div className="card" style={{ padding: 0, overflowX: "auto" }}>
            {result.results.length === 0 ? (
              <div className="empty">No player meets every criterion. Lower a threshold or see the near misses below.</div>
            ) : (
              <table className="table scout-table">
                <thead>
                  <tr>
                    <th aria-label="Select for comparison" />
                    <th>Tier</th>
                    <th>Player</th>
                    <th className="num">Min</th>
                    <th className="num">Team poss.</th>
                    {result.criteria.map((c) => (
                      <th key={c.key}>
                        {c.label} <span className="muted">≥{c.min_percentile}</span>
                      </th>
                    ))}
                    <th className="num">Weakest</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r) => {
                    const ref = playerSeasonRef(r.player_id, r.season_id);
                    return (
                      <tr key={ref}>
                        <td>
                          <input type="checkbox" checked={selected.includes(ref)} onChange={() => toggle(ref)}
                            disabled={!selected.includes(ref) && selected.length >= MAX_COMPARED}
                            aria-label={`Select ${r.player_name}`} />
                        </td>
                        <td><span className={`pill tier tier-${Math.min(r.tier, 3)}`}>{r.tier}</span></td>
                        <td>
                          <Link className="player-link" to={`/players/${r.player_id}/seasons/${r.season_id}`}>{r.player_name}</Link>
                          <div className="metric-sub">{r.teams.join(" / ")} · {r.competition}</div>
                        </td>
                        <td className="num">{formatMinutes(r.minutes)}</td>
                        <td className="num">{r.team_possession_pct === null ? "—" : `${Math.round(r.team_possession_pct)}%`}</td>
                        {r.criteria.map((v) => <CriterionCell key={v.key} value={v} />)}
                        <td className="num">{formatPercentile(r.weakest_percentile)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {result.near_misses.length > 0 && (
            <section style={{ marginTop: 22 }}>
              <h2 className="section-title">Near misses</h2>
              <p className="theme-note">
                Players who miss exactly one criterion by at most {result.near_miss_points} percentile points. Thresholds
                are noisy: in a half-season test, near misses performed almost as well as the shortlist later on.
              </p>
              <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                <table className="table scout-table">
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th>Missed</th>
                      <th className="num">Min</th>
                      {result.criteria.map((c) => <th key={c.key}>{c.label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {result.near_misses.map((m) => (
                      <tr key={playerSeasonRef(m.player_id, m.season_id)}>
                        <td>
                          <Link className="player-link" to={`/players/${m.player_id}/seasons/${m.season_id}`}>{m.player_name}</Link>
                          <div className="metric-sub">{m.teams.join(" / ")} · {m.competition}</div>
                        </td>
                        <td className="secondary">{labelOf(m.missed)} <span className="muted">by {m.gap.toFixed(1)}</span></td>
                        <td className="num">{formatMinutes(m.minutes)}</td>
                        {m.criteria.map((v) => <CriterionCell key={v.key} value={v} />)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <p className="muted cmp-rule">
            {result.method} Shortlists are a starting point: in a half-season test, shortlisted players stayed well above
            average later on (70th–86th percentile on the criteria), but fewer than half met every threshold again.
          </p>
        </>
      )}
    </>
  );
}
