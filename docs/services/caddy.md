<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# caddi backend (caddy)

The playbook can install and configure the **caddi backend** for you.

[caddi](https://caddy.courses) is a mobile-first, voice-first golf caddy. This service is its server side: the **sync/backup** endpoint for on-device course memories and the **LLM proxy** (the dex → Claude → user-model reasoning chain). The Flutter client and the crown-jewel per-user course-memory dataset are described in `apps/caddi/CLAUDE.md`.

> **Naming:** the product/app is **`caddi`** (with an *i*); the deployment identifiers use **`caddy`** (with a *y*, matching the domain `caddy.courses`): role `caddy-ar`, identifier `sgc-caddy`.

> **⚠️ Status:** local-only role (not published to GitHub) at `roles/mash/caddy/`, synced from `~/sgc/ansible/roles/caddy-ar/`. The **backend container image does not exist yet** (`caddy_container_image` is empty; `P3X-118/caddi-backend` is a placeholder), so `validate_config` fails until an image source is set. This is deployment scaffolding.

For details about configuring the role, see:
- 📁 `roles/mash/caddy/docs/configuring-caddy.md` locally
- 📁 `roles/mash/caddy/defaults/main.yml` for the full list of options

## Dependencies

This service requires the following other services:

- [Traefik](traefik.md) reverse-proxy server — on `caddy.courses` it runs **HTTP-only** behind a Cloudflare Tunnel (see [cloudflared](cloudflared.md)); Cloudflare terminates TLS at the edge.
- [Postgres](postgres.md) database — for sync/backup state.
- [cloudflared](cloudflared.md) — public ingress (the malp VM has no inbound).
- External: [dex](https://dex.sgc.ai) LLM (`http://10.20.0.55:8081`, via the host's 2nd NIC), LocalRecall (per-user RAG course memories), and authentik OIDC (`https://auth.caddy.courses/`).

## Usage

The role is referenced in `setup.yml` as `mash/caddy` and is enabled per-host:

```yaml
caddy_enabled: true
caddy_hostname: caddy.courses
# choose an image source (see the status note above)
```

Then deploy with `just setup-service caddy --limit caddy.courses` from `SGC/`.
