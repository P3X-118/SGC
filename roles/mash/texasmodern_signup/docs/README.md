# texasmodern_signup

SGC role that manages **only the `.env`** for the
`texasmodern-signup.eagledrive.live` AWS EC2 stack
(`tmw`, `169.254.0.130` on the SGC mesh), then restarts the compose
stack so a rotated secret takes effect.

## Scope: .env only

The stack at `/opt/tmw/infra/aws/` is:

- **caddy** — TLS termination + forward_auth gate (Cloudflare DNS-01)
- **web** — Expo bundle (nginx)
- **api** — Fastify intake API
- **db** — Postgres 16
- **migrate** — one-shot schema migrator
- **authentik-proxy** — goauthentik proxy outpost → shared Authentik on
  `bskypds.pro` over the SGC VPN mesh

**This role owns `/opt/tmw/infra/aws/.env` and nothing else.** The
`docker-compose.yml`, `Caddyfile`, and all app source are owned by the
TMW app's own deploy tool, `~/b2b/TexasModernWaste/bin/deploy.sh`, which
tars `api web infra` over `/opt/tmw` on every deploy. That tar
**excludes `.env`**, so the two systems coexist cleanly:

| Artifact | Owner |
|---|---|
| `api/`, `web/`, `infra/aws/docker-compose.yml`, `infra/aws/Caddyfile` | `bin/deploy.sh` (canonical repo `~/b2b/TexasModernWaste`) |
| `infra/aws/.env` (secrets) | this SGC role |

> History: this role previously also rendered `docker-compose.yml`,
> which fought `deploy.sh` — every app deploy reverted the role's compose
> and took the admin login + `tmw.eagledrive.live` down (2026-05-20).
> Compose ownership was moved entirely to the canonical source. The mesh
> `extra_hosts` pin, the `proxy:2025.10.3` image pin, and the
> `tmw.eagledrive.live` redirect now live in
> `~/b2b/TexasModernWaste/infra/aws/{docker-compose.yml,Caddyfile}`.

## Required vars (provide via vault)

- `texasmodern_signup_postgres_password`
- `texasmodern_signup_caddy_email`
- `texasmodern_signup_cloudflare_api_token`
- `texasmodern_signup_ntfy_auth_token`
- `texasmodern_signup_authentik_outpost_token`

## Authentik outpost token

The outpost API token is minted by the Authentik server when
`provision-texasmodern.py` runs. Re-run that script on bskypds and copy
the printed `OUTPOST_TOKEN=...` into vault:

```bash
ssh prod docker exec -e TMW_OIDC_SECRET=... -i pds-authentik-server \
    ak shell < ~/sgc/apps/authentik/scripts/sgc/provision-texasmodern.py \
    | grep OUTPOST_TOKEN
```
