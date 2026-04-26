# OCC IROPS Recovery Dashboard — Production Deploy Guide (Sprint 5)

This document covers the **internal pilot deploy** of the dashboard
behind a corporate VPN. It is *not* a public-internet deploy guide —
the auth layer here is intentionally lightweight (yaml-file
credentials) and is expected to be replaced by SSO/OIDC in a later
sprint.

## 1. Prerequisites

- Docker 24+ and Docker Compose v2.
- Outbound HTTPS to `pypi.org` for image build (or a private mirror).
- A copy of this repo on the host. No source-code modifications are
  needed for deploy.

## 2. Configure users

```bash
cp config/users.example.yaml config/users.yaml
```

Generate bcrypt password hashes for each pilot user:

```bash
python -c "
import streamlit_authenticator as stauth
hashes = stauth.Hasher.hash_passwords({
    'usernames': {
        'dm1':     {'password': 'CHANGEME-dm-password'},
        'viewer1': {'password': 'CHANGEME-viewer-password'},
    }
})
print(hashes)
"
```

Paste the resulting hashes into `config/users.yaml` and replace the
`cookie.key` with a 64-character random hex string:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`config/users.yaml` is gitignored — do not commit.

Roles supported:

| role     | rights                                                       |
|----------|--------------------------------------------------------------|
| `dm`     | Full access: run analysis, edit settings, view audit log.    |
| `viewer` | Read-only: run analysis + download exports. No settings/audit. |

## 3. Launch

```bash
docker compose up --build -d
```

Then open <http://localhost:8501> on the host (or the VPN-routed URL).

## 4. Healthcheck

The container exposes Streamlit's native healthcheck at
`/_stcore/health`. Docker Compose polls it every 30 seconds; you can
also wire it into your monitoring system:

```bash
curl --fail http://<host>:8501/_stcore/health
# => "ok"
```

## 5. Persistence

A named Docker volume `occ_irops_dashboard_data` is mounted at
`/app/data` in the container. It contains:

- `runs.db` — SQLite with three tables: `runs`, `settings`,
  `audit_events`.

To back up the database:

```bash
docker compose exec dashboard sh -c "sqlite3 /app/data/runs.db .dump" \
  > runs-$(date +%Y%m%d).sql
```

To inspect the database from the host:

```bash
docker compose exec dashboard sqlite3 /app/data/runs.db \
  "SELECT created_at, user, action FROM audit_events \
   ORDER BY created_at DESC LIMIT 20"
```

## 6. Disabling auth (development only)

Setting `OCC_AUTH_DISABLED=1` in the container environment makes the
dashboard sign every request in as a hard-coded `localdev` user with
role `dm`. Useful for local smoke-testing; **never set this in a
production deploy.**

```yaml
environment:
  OCC_AUTH_DISABLED: "1"  # DEV ONLY
```

## 7. Ingress / TLS

This compose file does not include nginx. In production, terminate
TLS at your existing corporate proxy / load balancer and forward to
`http://<dashboard-host>:8501`. Streamlit handles WebSocket upgrades
on the same port.

## 8. Audit log export

The dashboard's "Audit log (DM-only)" expander has a **Download CSV**
button. The schema is simply
`(id, user, action, payload_json, created_at)` so it ingests cleanly
into Splunk / Datadog / a corporate SIEM.

## 9. Rotating credentials

To change a password without rebuilding the image:

1. Generate a new bcrypt hash (see step 2).
2. Edit `config/users.yaml` on the host (it's mounted read-only into
   the container).
3. Restart the container: `docker compose restart dashboard`.
