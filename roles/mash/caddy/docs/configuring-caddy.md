<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Configuring the caddi backend (`caddy`)

This role deploys the caddi backend (sync/backup + LLM proxy) as a Docker container behind Traefik, backed by PostgreSQL. Enable it in the SGC playbook per the standard 4-step service pattern (`requirements.yml`, `setup.yml`, `group_vars/mash_servers`, docs) and set the host-specific values in `inventory/host_vars/caddy.courses/`.

## Prerequisites

- A PostgreSQL server. The SGC playbook derives the DB name/username/password for this service through `postgres_autom_itemized` and the `db.caddy` password-derivation salt.
- The [`cloudflared`](https://github.com/P3X-118/cloudflared-ar) role on the same host for public ingress, with Traefik configured HTTP-only (see that role's docs).
- An authentik OIDC application (`caddy`) at `https://auth.caddy.courses/`.

## Minimum required settings

```yaml
caddy_enabled: true
caddy_hostname: caddy.courses            # or api.caddy.courses

# Image source — REQUIRED (one of these). The backend image does not exist yet:
caddy_container_image: ""                # e.g. a published caddi-backend image, OR:
# caddy_container_image_self_build: true # build from caddy_container_image_self_build_repo

# Database (SGC group_vars derives these on the host):
caddy_database_hostname: "{{ postgres_connection_hostname }}"
caddy_database_password: "..."           # derived via password_hash(..., 'db.caddy', ...)

# Secrets:
caddy_environment_variables_jwt_secret: "..."          # random string
caddy_environment_variables_oidc_client_secret: "..."  # from the authentik OIDC app
```

## LLM / RAG / OIDC contract

Defaults come from [`apps/caddi/CLAUDE.md`](../../../apps/caddi/CLAUDE.md); override per host as needed:

```yaml
caddy_environment_variables_dex_base_url: "http://10.20.0.55:8081"   # dex/LocalAI (via 2nd NIC)
caddy_environment_variables_dex_model: ""                            # TODO: pin one model, keep it warm
caddy_environment_variables_anthropic_api_key: ""                    # Claude fallback (empty = disabled)
caddy_environment_variables_localrecall_base_url: ""                 # e.g. http://<host>:8080/api
caddy_environment_variables_oidc_issuer: "https://auth.caddy.courses/application/o/caddy/"
caddy_environment_variables_oidc_client_id: caddy
```

> **dex discipline:** dex serves one model at a time and reloads on model switch. Keep one model per workload, serialize calls, use ≥120s timeouts, and read `content || reasoning` for JSON tasks. See `~/.claude/CLAUDE.md`.

> **Data is sacred:** per-user course memories are the crown-jewel dataset. The sync/backup path must be lossless (append/merge, never silent-drop) and per-user isolated (one LocalRecall collection per authentik subject). See `apps/caddi/CLAUDE.md`.

## Traefik / ingress

`caddy_container_labels_traefik_enabled` defaults to `true`. On `caddy.courses` the host disables the `web-secure` entrypoint + ACME, so the router entrypoint resolves to `web` (HTTP) and no certificate is issued locally — Cloudflare terminates TLS at the edge and cloudflared forwards to Traefik.
