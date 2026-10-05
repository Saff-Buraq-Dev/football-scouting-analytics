#!/bin/sh
# One-shot data bootstrap, run by the "bootstrap" service of the stack.
# Downloads StatsBomb Open Data on this host, loads PostgreSQL and computes the analytics snapshots.
# Idempotent: exits immediately if the snapshots already exist (set FORCE_BOOTSTRAP=1 to rebuild).
set -eu

echo "Waiting for PostgreSQL..."
python - <<'PY'
import time
import psycopg
from football_platform.database.connection import database_url
for attempt in range(60):
    try:
        psycopg.connect(database_url(), connect_timeout=3).close()
        break
    except psycopg.OperationalError:
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL not reachable")
PY

python -m football_platform.database.migrate

if [ "${FORCE_BOOTSTRAP:-0}" != "1" ] && python - <<'PY'
import sys
from football_platform.database.connection import connect
with connect() as conn:
    players = conn.execute("SELECT count(*) FROM player_seasons").fetchone()[0]
    teams = conn.execute("SELECT count(*) FROM team_seasons").fetchone()[0]
sys.exit(0 if players and teams else 1)
PY
then
    echo "Analytics snapshots already present: nothing to do (FORCE_BOOTSTRAP=1 to rebuild)."
    exit 0
fi

echo "Step 1/4: download and ingest StatsBomb Open Data (~5 min, ~4.3 GB)"
python -m football_platform.pipeline.ingest
echo "Step 2/4: load PostgreSQL (~5 min)"
python -m football_platform.pipeline.load_database
echo "Step 3/4: player analytics snapshot"
python -m football_platform.reports.player_season_report
echo "Step 4/4: team analytics snapshot"
python -m football_platform.reports.team_season_report

if [ "${KEEP_PIPELINE_FILES:-false}" != "true" ]; then
    echo "Removing downloaded and intermediate files (KEEP_PIPELINE_FILES=true to keep them)"
    rm -rf /app/data/raw /app/data/canonical
fi
echo "Bootstrap complete."
