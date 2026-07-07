# learningwell

Manages the `.env` for **The Learning Well** (`thelearningwell.eagledrive.live`) —
a prepackaged school-supply store (Next.js + Stripe) — and (re)starts its Docker
Compose stack so changes take effect. Deployed on the same EC2 host as
`texasmodern_signup`, sharing that host's Caddy via a drop-in vhost.

## Scope (mirrors `texasmodern_signup`)

This role owns **only** `{{ learningwell_compose_path }}/.env`. The compose files,
Caddy vhost (`infra/caddy/learningwell.caddy`), and all app source are owned by
the app's own deploy tool — `~/b2b/learningWell/bin/deploy.sh` — which tars the
repo over `{{ learningwell_base_path }}` and **excludes** `.env`. So:

- `deploy.sh` ships code + compose + Caddy vhost and **builds the image**.
- this role ships the `.env` (`build: never` on restart).

`NEXT_PUBLIC_SITE_URL` and `AMAZON_AFFILIATE_TAG` are baked at **build** time
(deploy.sh); `STRIPE_SECRET_KEY` is read at **runtime** (this role's restart
applies it).

## Deploy order (first time)

1. Create the Cloudflare DNS record for `thelearningwell.eagledrive.live`.
2. One-time on the host's Caddy: mount `/opt/caddy-sites:/etc/caddy/sites:ro`
   and add `import /etc/caddy/sites/*.caddy` to its Caddyfile.
3. `bin/deploy.sh` from the Learning Well repo (ships code, builds the image,
   brings the stack up, drops the vhost, reloads Caddy).
4. `just install-service learningwell -e target=texasmodern-signup.eagledrive.live`
   to render `.env`. (Safe to run before step 3 — it just notes the code isn't
   there yet and skips the restart.)

## Required vars

`learningwell_hostname`, `learningwell_site_url`, `learningwell_caddy_network`.
Secrets (`learningwell_deposyt_security_key`, `learningwell_smtp_pass`, etc.) via
vault — or set directly in the host `.env` for launch. See `defaults/main.yml`.
