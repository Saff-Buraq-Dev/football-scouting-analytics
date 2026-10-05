import type { ReliabilityBand } from "../api";
import { RELIABILITY_TEXT } from "../format";

const DOTS: Record<ReliabilityBand, number> = { low: 1, medium: 2, high: 3 };

/** Reliability of a per-90 value (Phase 4.1 §4). Text carries the meaning; dots only echo it. */
export function ReliabilityBadge({ band }: { band: ReliabilityBand | null }) {
  if (band === null) return null;
  return (
    <span className="badge" title={RELIABILITY_TEXT[band]}>
      <span className="badge-dots" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <i key={i} className={i <= DOTS[band] ? "on" : undefined} />
        ))}
      </span>
      {band}
    </span>
  );
}
