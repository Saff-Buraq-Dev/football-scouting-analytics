# Deploying on a self-hosted Portainer

The stack runs three services from one image (`ghcr.io/saff-buraq-dev/football-scouting-analytics`):

| Service | Role |
|---|---|
| `db` | PostgreSQL 17, persistent volume, **no published port** |
| `bootstrap` | one-shot: downloads StatsBomb Open Data **on your host**, loads the database, computes the analytics snapshots, then exits. It does nothing on later starts if the data is already there |
| `app` | web interface + API on one port (default 8080) |

The image contains code only. Football data is downloaded directly from StatsBomb's repository by your server and never stored in an image or registry (StatsBomb User Agreement, decision D004).

## Requirements

- Docker host managed by Portainer (amd64 or arm64)
- **4 GB RAM** for the bootstrap (measured peak: 3.4 GB, while analytics run over 5.3M events in memory); the app alone needs about 100 MB
- **10 GB free disk** during the bootstrap (raw files are deleted at the end); about 3.5 GB afterwards (database volume)
- Outbound internet access to `github.com` / `raw.githubusercontent.com` for the first start

## Steps

1. **Image.** GitHub publishes `ghcr.io/saff-buraq-dev/football-scouting-analytics` on every push to `main`
   (CI job "Publish Docker image"). It is public (linked to this public repository), so Portainer needs no
   credentials. If the package is ever made private, add `ghcr.io` as a registry in Portainer with a GitHub token
   that has `read:packages`.
2. In Portainer: **Stacks → Add stack**. Name it `football-scouting`, choose *Web editor* and paste
   [`portainer-stack.yml`](portainer-stack.yml), or choose *Repository* and point to this repository with compose path
   `deploy/portainer-stack.yml`.
3. **Environment variables:**
   - `POSTGRES_PASSWORD`: required, **letters and digits only** (it is embedded in a connection URL)
   - `APP_PORT`: optional, default `8080`
   - `IMAGE_TAG`: optional, default `latest` (use a commit SHA to pin a version)
4. **Deploy the stack.** Follow the `bootstrap` container logs: about 15 minutes on a typical connection
   (download ~5 min, database load ~5 min, analytics ~1 min). It ends with `Bootstrap complete.` and exits (status *Exited (0)*, which is expected).
5. Open `http://<server>:8080`. Before the bootstrap finishes, the site loads but has no data yet.

## Exposing it publicly

Put it behind your reverse proxy (Traefik, Nginx Proxy Manager, Caddy…) with HTTPS, pointing to the `app` port.
The app trusts `X-Forwarded-*` headers. The API is read-only and serves aggregated metrics only.

## Operations

| Task | How |
|---|---|
| Update the app | redeploy the stack with *Re-pull image* (data is kept in the volumes) |
| Rebuild data and analytics | set `FORCE_BOOTSTRAP=1` on the `bootstrap` service and start it once, then remove the variable |
| Keep downloaded files (for debugging) | `KEEP_PIPELINE_FILES=true` on `bootstrap` |
| Back up | the `pgdata` volume (or `pg_dump` inside the `db` container) |

## Troubleshooting

- `bootstrap` exits with an error: read its logs. Network errors during the download are retried; re-running the
  container resumes (already downloaded files are skipped).
- The site shows "no data": the bootstrap has not finished, or failed. Check its logs.
- Out of memory during "Step 3/4": give the host or container more RAM (4 GB recommended).
