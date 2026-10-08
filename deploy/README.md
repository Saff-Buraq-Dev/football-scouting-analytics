# Deploying on a self-hosted Portainer

The stack runs three services from one image (`safsaf90/football-scouting-analytics` on Docker Hub):

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

1. **Image.** GitHub Actions builds and pushes `safsaf90/football-scouting-analytics` (amd64 + arm64) to Docker Hub
   on every push to `main` that passes the tests. One-time setup:
   - Docker Hub → Account settings → **Personal access tokens** → generate a token with *Read & Write* access.
   - GitHub repository → Settings → **Secrets and variables → Actions** → add `DOCKERHUB_USERNAME` = `safsaf90`
     and `DOCKERHUB_TOKEN` = the token.
   - Re-run the latest CI workflow (Actions tab → *Re-run all jobs*), or push a commit.

   Without these secrets the CI publishing step is skipped with a warning. A public Docker Hub repository needs no
   credentials in Portainer. If you make it private, add Docker Hub as a registry in Portainer.
2. In Portainer: **Stacks → Add stack**. Name it `football-scouting`, choose *Web editor* and paste
   [`portainer-stack.yml`](portainer-stack.yml), or choose *Repository* and point to this repository with compose path
   `deploy/portainer-stack.yml`.
3. **Environment variables:**
   - `POSTGRES_PASSWORD`: required, **letters and digits only** (it is embedded in a connection URL)
   - `APP_PORT`: optional, default `8080`
   - `IMAGE_TAG`: optional, default `latest` (use a commit SHA to pin a version)
   - `AUTH_PROVIDER` and `OIDC_*`: optional, for the recruitment board (see [Login](#login-recruitment-board))
4. **Deploy the stack.** Follow the `bootstrap` container logs: about 15 minutes on a typical connection
   (download ~5 min, database load ~5 min, analytics ~1 min). It ends with `Bootstrap complete.` and exits (status *Exited (0)*, which is expected).
5. Open `http://<server>:8080`. Before the bootstrap finishes, the site loads but has no data yet.

## Exposing it publicly

Put it behind your reverse proxy (Traefik, Nginx Proxy Manager, Caddy…) with HTTPS, pointing to the `app` port.
The app trusts `X-Forwarded-*` headers. The API is read-only and serves aggregated metrics only.

## Login (recruitment board)

The analytics pages are public. The recruitment board (shortlists, tags, notes) needs a login, provided by an
external identity service (decision D032). Set `AUTH_PROVIDER` on the stack:

| `AUTH_PROVIDER` | Behaviour |
|---|---|
| `disabled` (default) | No login, no board. |
| `dev` | Everyone who can open the site is the same "Local user". **Only** for an instance reachable by you alone (LAN, VPN). |
| `oidc` | Real accounts through Amazon Cognito or any OpenID Connect provider (Keycloak, Auth0, Entra ID…). |

### Amazon Cognito

1. AWS console → Cognito → **Create user pool**. Application type: **Single-page application (SPA)**, which creates
   an app client **without a client secret** (the browser cannot keep a secret). Sign-in identifier: email.
   Return URL: `https://<your-host>/auth/callback`.
2. In the app client's **Login pages** settings, check:
   - Allowed callback URLs: `https://<your-host>/auth/callback` (add `http://localhost:5173/auth/callback` for local development)
   - OAuth grant type: **Authorization code grant**
   - Scopes: `openid`, `email`, `profile`
3. The user pool needs a domain (Cognito domain or your own): it hosts the login page.
4. Create users in the console, or enable self-registration.
5. Stack environment:
   - `AUTH_PROVIDER=oidc`
   - `OIDC_ISSUER=https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`
   - `OIDC_CLIENT_ID=<app client id>`
6. Redeploy. "Log in" appears in the top bar and redirects to the Cognito login page.

Cognito only accepts HTTPS callback URLs (except `localhost`), so the site must be behind your HTTPS reverse proxy.
The server only verifies tokens: it never receives passwords and stores no secret. Board data stays in your database
(`app_users`, `shortlists`, `player_tags`, `player_notes`) and is included in the `pgdata` backup.

Limits (v1): no refresh token, so users log in again after the token expires (1 hour by default); "Log out" ends the
session in the browser, not on Cognito. The flow is covered by automated tests with locally signed tokens, but has
not yet been run against a live user pool: check it once after your first setup.

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
