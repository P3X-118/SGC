# texasmodern_signup

SGC role for the `texasmodern-signup.eagledrive.live` AWS EC2 stack.

The host (`tmw`, `169.254.0.130` on the SGC mesh) runs a self-contained
docker-compose project at `/opt/tmw/infra/aws/`:

- **caddy** — TLS termination + forward_auth gate (Cloudflare DNS-01)
- **web** — Expo bundle (nginx)
- **api** — Fastify intake API
- **db** — Postgres 16
- **migrate** — one-shot schema migrator
- **authentik-proxy** — goauthentik proxy outpost, connects to the shared
  Authentik on `bskypds.pro` over the SGC VPN mesh

This role owns the compose file and `.env`. It does **not** clone or
manage the application source under `/opt/tmw/{api,web,caddy,...}` —
that is placed on the host out-of-band.

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

## Image pinning

`texasmodern_signup_authentik_proxy_image_tag` MUST match the Authentik
server's exact patch version on bskypds (currently `2025.10.3`). The
floating `:2025.10` tag drifts ahead and will crash-loop the outpost
when the server's API response is missing a field the newer outpost
requires. Bump the server and the outpost in the same change.

## Mesh dependency

The outpost reaches the server via VPN mesh — `extra_hosts` pins
`auth.eagledrive.live` to `texasmodern_signup_authentik_mesh_ip`
(default `169.254.0.127`). The public `128.254.161.222` is not
reliably reachable from this EC2; do not regress this setting.
