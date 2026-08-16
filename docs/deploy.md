# Deploying to Hetzner

Merge to `main` → GitHub Actions runs the tests, builds one Docker image,
pushes it to GHCR, SSHes into the Hetzner box and restarts the container there.
If the new image doesn't answer `/api/health`, the previous one goes back up
automatically and the run fails red.

```
merge to main
  └─ test    pytest (232 tests) + tsc --noEmit + vite build
  └─ build   docker build → ghcr.io/vikteur/spotify-to-rekordbox:<sha>
  └─ deploy  scp compose+script → ssh → pull → up -d → health-check
                                                  └─ unhealthy? roll back
```

## What actually runs on the server

**One container.** `server/main.py` mounts the built client (`dist/`) as static
files, so uvicorn serves the API *and* the React app on port 8000. There is no
separate web service to deploy.

It publishes on `127.0.0.1:8000` only — nothing from the internet reaches it
except through a reverse proxy on the same box.

**State lives in a Docker volume** (`rekordmatch_data` → `/app/data`). That's
`library.db`: libraries, imported playlists, couples, magic-link tokens.
Deploys replace the container, never the volume. It is *not* in git and *not*
in the image — back it up (see below).

## One-time setup

### 1. The server

```bash
scp deploy/bootstrap.sh root@YOUR_SERVER_IP:/tmp/
ssh root@YOUR_SERVER_IP "bash /tmp/bootstrap.sh"
```

Idempotent — installs Docker only if missing, creates the `deploy` user,
opens 80/443, creates `/opt/rekordmatch`.

### 2. A key for CI

On your machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rekordmatch_deploy -C "github-actions" -N ""
ssh-copy-id -i ~/.ssh/rekordmatch_deploy.pub deploy@YOUR_SERVER_IP
ssh-keyscan -H YOUR_SERVER_IP          # → paste into SSH_KNOWN_HOSTS
cat ~/.ssh/rekordmatch_deploy          # → paste into SSH_PRIVATE_KEY
```

### 3. Repo secrets

`Settings → Secrets and variables → Actions`:

| Secret | Value | Required |
|---|---|---|
| `HETZNER_HOST` | server IP or hostname | yes |
| `HETZNER_USER` | `deploy` | yes |
| `SSH_PRIVATE_KEY` | the whole private key, incl. BEGIN/END lines | yes |
| `SSH_KNOWN_HOSTS` | `ssh-keyscan` output | recommended |
| `APP_DIR` | defaults to `/opt/rekordmatch` | no |

`GITHUB_TOKEN` is automatic — no PAT needed, the server logs in to GHCR with
the workflow's own token.

### 4. The server's `.env`

```bash
scp deploy/.env.example deploy@YOUR_SERVER_IP:/opt/rekordmatch/.env
ssh deploy@YOUR_SERVER_IP "chmod 600 /opt/rekordmatch/.env && nano /opt/rekordmatch/.env"
```

Set the domain and Spotify keys. CI rewrites `APP_IMAGE` on every deploy;
leave the rest alone.

### 5a. If the box already runs nginx (this one does)

`46.224.211.159` already serves `viktorvansteenweghen.com` through system
nginx on 80/443, so the bundled Caddy stays **off** — it would fail to bind.
Leave `COMPOSE_PROFILES` commented and use `deploy/nginx/rekord.conf`: it
only terminates TLS and forwards — the app does its own login now, so there
is no htpasswd file any more (remove `/etc/nginx/.htpasswd-rekord` if it's
still around).

```bash
scp deploy/nginx/rekord.conf root@SERVER:/etc/nginx/sites-available/rekord
ssh root@SERVER "ln -sfn /etc/nginx/sites-available/rekord /etc/nginx/sites-enabled/rekord && nginx -t && systemctl reload nginx"
```

Note `nginx -t` before every reload — a bad config fails the test and leaves
the running nginx untouched, so the other sites on the box stay up.

### 5b. TLS via the bundled Caddy

Uncomment `COMPOSE_PROFILES=proxy` and `APP_DOMAIN` in `.env` to use the
bundled Caddy — it gets a Let's Encrypt cert on first boot, provided the A
record already points at the box. Already running nginx or Traefik? Leave
those commented and point your existing proxy at `127.0.0.1:8000`.

### 5c. The admin account

Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env` (min 8 characters). On
first boot, if no admin exists yet, the app creates that account; changing
the variables later does nothing on purpose. Forgot the password?

```bash
docker compose exec app python -m server.create_user viktor --reset
```

DJ accounts are made by the admin inside the app (sidebar → **DJ accounts**)
or with the same CLI. Couples can also be created from the shell:

```bash
docker compose exec app python -m server.create_couple "Sofie & Jan" 2026-05-25 --dj sarah
```

Then merge to `main`.

## Who can reach what

The app enforces its own access (`server/auth.py` / `server/auth_api.py`):
every `/api` route requires a session cookie except `/api/health` (uptime
monitoring, returns only `{"ok":true}`), `/api/auth/login`/`logout`, and the
`/api/guest/*` routes, where the magic-link token in the path *is* the auth.
A route-walk test (`tests/test_auth.py`) fails the build if a future route
forgets its guard. The static bundle and `/g/*` pages are public — they show
nothing without a session or token.

Roles: the **admin** sees every DJ's couples and libraries and is the only
one who manages accounts; a **DJ** sees only their own; **couples/friends**
only ever hold a magic link.

`/g/*` also gets `Referrer-Policy: no-referrer` at the proxy, so a guest
tapping through to Spotify can't leak their magic link in a `Referer` header.
The proxy must pass `X-Forwarded-Proto` (both shipped configs do) — the app
marks its session cookie `Secure` only when it sees https there.

## Day-to-day

```bash
ssh deploy@YOUR_SERVER_IP
cd /opt/rekordmatch

docker compose ps                  # what's up
docker compose logs -f app         # tail logs
docker compose restart app         # kick it
curl localhost:8000/api/health     # {"ok":true}
```

**Roll back by hand** — every deployed sha is still in GHCR:

```bash
./deploy.sh ghcr.io/vikteur/spotify-to-rekordbox:<older-sha>
```

**Back up the database** — a consistent copy, safe to take while the app is
running (`.backup` takes SQLite's own lock; a plain `cp` of a live DB can tear):

```bash
docker compose exec -T app python -c "import sqlite3; s=sqlite3.connect('/app/data/library.db'); d=sqlite3.connect('/app/data/backup.db'); s.backup(d); d.close(); s.close()"
docker compose cp app:/app/data/backup.db ./library-$(date +%F).db
docker compose exec -T app rm /app/data/backup.db
```

Worth a weekly cron — the magic-link tokens live in there, and regenerating
them means re-sending every couple their link.

## Known limitation

`POST /api/scan` walks a **local folder** of audio files and exports playlists
containing local paths. On a remote server there is no music folder, so the
scan/match half of the app is effectively local-only. What genuinely belongs
on this box is the couples intake and the `/g/<token>` guest magic links —
those are meant to be reached from someone else's phone.
