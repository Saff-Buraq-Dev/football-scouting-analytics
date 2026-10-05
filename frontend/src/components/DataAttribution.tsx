/** Data attribution required by the StatsBomb Public Data User Agreement §1.4 (D004). */
export function DataAttribution() {
  return (
    <a className="attribution" href="https://github.com/hudl/open-data" target="_blank" rel="noreferrer">
      <span>Data</span>
      <span className="attribution-logo">
        <img src="/attribution/statsbomb-logo.png" alt="StatsBomb" width={110} height={18} />
      </span>
      <span>Open Data · derived, aggregated metrics only</span>
    </a>
  );
}
