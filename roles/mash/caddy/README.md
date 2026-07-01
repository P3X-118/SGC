<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# caddi backend (`caddy`) Ansible role

This is an [Ansible](https://www.ansible.com/) role which installs the **caddi backend** to run as a [Docker](https://www.docker.com/) container wrapped in a systemd service.

[caddi](../../../apps/caddi) is a mobile-first, voice-first golf caddy. This role deploys its server side: the **sync/backup** endpoint for on-device course memories and the **LLM proxy** (the dex → Claude → user-model reasoning chain), sitting behind Traefik and backed by PostgreSQL.

> **Naming:** the product/app is **`caddi`** (with an *i*); all deployment identifiers use **`caddy`** (with a *y*, matching the domain `caddy.courses`): role repo `caddy-ar`, var prefix `caddy_`, service identifier `sgc-caddy`.

> **⚠️ Status:** the backend **container image does not exist yet**. `caddy_container_image` is empty and `caddy_container_image_self_build_repo` (`P3X-118/caddi-backend`) is a placeholder. `validate_config` will fail until you point the role at a real image source. This role is the deployment scaffold; wire the image in once the backend is built.

This role *implicitly* depends on:

- [`playbook_help`](https://github.com/P3X-118/playbook_help)
- [`systemd_docker_base`](https://github.com/P3X-118/systemd_docker_base)
- a PostgreSQL server (the SGC `postgres` role, via the host's `postgres_autom_itemized` automation)

Check [`defaults/main.yml`](defaults/main.yml) for the full list of supported options. Refer to [this page](docs/configuring-caddy.md) for details about setting up the service with this role.

## Environment contract

The rendered `env` file mirrors the ecosystem contracts documented in [`apps/caddi/CLAUDE.md`](../../../apps/caddi/CLAUDE.md): `DATABASE_URL` (PostgreSQL), `DEX_BASE_URL` (dex/LocalAI, reached via the host's second NIC at `http://10.20.0.55:8081`), `ANTHROPIC_API_KEY` (Claude fallback), `LOCALRECALL_BASE_URL` (per-user RAG course memories), and the authentik `OIDC_*` settings (the backend is the confidential OIDC client for the PKCE mobile flow). The exact variable names the backend consumes must be confirmed when the backend image is built.

## Ingress on `caddy.courses`

On the `caddy.courses` host, Traefik runs **HTTP-only behind a Cloudflare Tunnel** (see the [`cloudflared`](https://github.com/P3X-118/cloudflared-ar) role). The host's `group_vars`/`host_vars` disable the `web-secure` entrypoint and ACME, so the Traefik router entrypoint resolves to `web` and no public certificate is issued here — Cloudflare terminates TLS at its edge.

## Release model

Follows the SGC 3-branch model (`main` / `sgc-dev` / `sgc`); production releases on `sgc` are tagged by appending an incrementing `-N` suffix.

## Development

You can optionally install [pre-commit](https://pre-commit.com/) so that simple mistakes are checked before changes are pushed. See [`.pre-commit-config.yaml`](./.pre-commit-config.yaml).
