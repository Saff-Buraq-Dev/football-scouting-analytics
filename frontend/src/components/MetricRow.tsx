import type { MetricView } from "../api";
import { formatPercentile, formatTotal, formatValue } from "../format";
import { PercentileBar } from "./PercentileBar";
import { ReliabilityBadge } from "./ReliabilityBadge";

export function MetricRow({ metric, populationLabel }: { metric: MetricView; populationLabel: string }) {
  const total = formatTotal(metric);
  return (
    <div className="metric-row">
      <div>
        <div className="metric-name">{metric.label}</div>
        <div className="metric-sub">
          {metric.unit === "per_90" ? "per 90" : "ratio"}
          {total !== null && ` · ${total} total`}
        </div>
        <ReliabilityBadge band={metric.reliability_band} />
      </div>
      <PercentileBar metric={metric} populationLabel={populationLabel} />
      <div className="metric-value">{formatValue(metric)}</div>
      <div className="metric-pct" aria-label="percentile">{formatPercentile(metric.percentile)}</div>
    </div>
  );
}

/** Column headers for a theme card: what each column means, once. */
export function ScaleLegend() {
  return (
    <div className="scale-legend" aria-hidden="true">
      <span />
      <span className="ticks">
        <span>0</span>
        <span>median</span>
        <span>100</span>
      </span>
      <span>value</span>
      <span>pct</span>
    </div>
  );
}
