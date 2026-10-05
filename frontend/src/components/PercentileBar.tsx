import { useId } from "react";
import type { MetricView } from "../api";
import { NOTE_TEXT, RELIABILITY_TEXT, formatPercentile, formatTotal, formatValue } from "../format";

interface Props {
  metric: MetricView;
  populationLabel: string;
}

/**
 * Percentile within the reference population, as a meter (0-100) with the median marked.
 * One hue for every bar: a percentile is descriptive, not "good" or "bad" (Phase 4 doc).
 */
export function PercentileBar({ metric, populationLabel }: Props) {
  const tooltipId = useId();
  const { percentile } = metric;

  if (percentile === null) {
    return (
      <span className="pbar-empty">
        {metric.percentile_note ? NOTE_TEXT[metric.percentile_note] : "Not ranked"}
        {metric.regressed !== null && (
          <span className="pbar-regressed">
            Regressed estimate <b>{metric.regressed.toFixed(2)}</b> per 90
          </span>
        )}
      </span>
    );
  }

  const total = formatTotal(metric);
  const lowReliability = metric.reliability_band === "low";
  return (
    <div
      className="pbar"
      tabIndex={0}
      role="img"
      aria-label={`${metric.label}: percentile ${formatPercentile(percentile)} among ${populationLabel}`}
      aria-describedby={tooltipId}
    >
      <div className="pbar-track">
        <div className={`pbar-fill${lowReliability ? " low" : ""}`} style={{ width: `${Math.max(percentile, 1.5)}%` }} />
        <div className="pbar-median" aria-hidden="true" />
      </div>
      <div className="tooltip" role="tooltip" id={tooltipId}>
        <strong>{formatPercentile(percentile)}th percentile</strong>
        <span>among {populationLabel}</span>
        <dl>
          <dt>{metric.unit === "per_90" ? "Per 90" : "Value"}</dt>
          <dd>{formatValue(metric)}</dd>
          {total !== null && (
            <>
              <dt>Season total</dt>
              <dd>{total}</dd>
            </>
          )}
          {metric.regressed !== null && (
            <>
              <dt>Regressed estimate</dt>
              <dd>{metric.regressed.toFixed(2)}</dd>
            </>
          )}
          {metric.reliability_band !== null && (
            <>
              <dt>Reliability</dt>
              <dd>{RELIABILITY_TEXT[metric.reliability_band]}</dd>
            </>
          )}
        </dl>
      </div>
    </div>
  );
}
