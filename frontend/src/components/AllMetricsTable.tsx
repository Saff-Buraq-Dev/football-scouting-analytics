import type { MetricView } from "../api";
import { NOTE_TEXT, formatPercentile, formatTotal, formatValue } from "../format";

/** Every metric as a table: the accessible equivalent of the bars, plus metrics outside the template. */
export function AllMetricsTable({ metrics }: { metrics: MetricView[] }) {
  return (
    <details className="all-metrics card">
      <summary>All metrics ({metrics.length})</summary>
      <table className="table">
        <thead>
          <tr>
            <th>Metric</th>
            <th className="num">Value</th>
            <th className="num">Total</th>
            <th className="num">Percentile</th>
            <th className="num">Regressed</th>
            <th>Reliability</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.key}>
              <td>{m.label} <span className="muted">{m.unit === "per_90" ? "per 90" : ""}</span></td>
              <td className="num">{formatValue(m)}</td>
              <td className="num">{formatTotal(m) ?? ""}</td>
              <td className="num" title={m.percentile_note ? NOTE_TEXT[m.percentile_note] : undefined}>
                {formatPercentile(m.percentile)}
              </td>
              <td className="num">{m.regressed !== null ? m.regressed.toFixed(2) : ""}</td>
              <td className="muted">{m.reliability_band ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
