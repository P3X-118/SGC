<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Stoked

The playbook can install and configure [Stoked](https://github.com/P3X-118/stoked) for you.

Stoked is a self-hostable, Discord-like chat platform (a fork of [Revolt](https://revolt.chat/)) with text channels, voice/video, file uploads and push notifications. It is a self-contained stack — the role brings up its own MongoDB, Redis/KeyDB, RabbitMQ and MinIO alongside the application services, so it does not depend on the shared SGC Postgres.

For details about configuring the [Ansible role for Stoked](https://github.com/P3X-118/stoked-ar), you can check them via:
- 🌐 [the role's repository](https://github.com/P3X-118/stoked-ar) online
- 📁 `roles/galaxy/stoked/` locally, if you have [fetched the Ansible roles](../installing.md)

## Architecture

A single Stoked instance is composed of the following containers. Everything is published on one hostname (`stoked_hostname`) and routed by path; the web client is the catch-all. Identifiers are prefixed per host (e.g. `yo-stoked-api`) via `service_id_prefix`.

| Component | Image (`legitservices/…:sgc`) | Route | Port | Exposure |
| --- | --- | --- | --- | --- |
| Web client | `stoked-web` | `Host(`​`stoked_hostname`​`)` (priority 1, catch-all) | 5000 | public |
| API (delta) | `stoked-api` | `/api` | 14702 | public |
| Events (bonfire) | `stoked-events` | `/ws` (WebSocket) | 14703 | public |
| Autumn (files) | `stoked-file-server` | `/autumn` | 14704 | public |
| January (embed proxy) | `stoked-proxy` | `/january` | 14705 | public |
| Gifbox | `stoked-gifbox` | `/gifbox` | 14706 | public |
| LiveKit (WebRTC SFU) | `livekit-server` | `/livekit` + direct RTC | 7880 / 7881 tcp, 50000-50100 udp | public |
| Crond (cleanup) | `stoked-crond` | — | — | internal |
| Pushd (push) | `stoked-pushd` | — | — | internal |
| Voice ingress | `stoked-voice-ingress` | — | — | internal |
| MongoDB | `docker.io/mongo` | — | — | internal |
| Redis / KeyDB | `eqalpha/keydb` | — | — | internal |
| RabbitMQ | `rabbitmq:4` | — | — | internal |
| MinIO (+ createbuckets) | `minio/minio`, `minio/mc` | — | — | internal |

Application images are pinned to the `{{ stoked_version }}` tag (default `sgc`). Each component can be toggled individually with its `stoked_<component>_enabled` flag (all default to `true` when `stoked_enabled` is set).

## Dependencies

This service requires the following other services:

- [Traefik](traefik.md) reverse-proxy server

> [!IMPORTANT]
> LiveKit voice/video needs RTC ports reachable from the internet: `7881/tcp` and `50000-50100/udp`. On cloud hosts (e.g. AWS) these must be opened in the **security group / cloud firewall**, not just the host firewall.

## Adjusting the playbook configuration

To enable this service, add the following configuration to the host's `inventory/host_vars/<host>/vars.yml` file and re-run the [installation](../installing.md) process:

```yaml
########################################################################
#                                                                      #
# stoked                                                               #
#                                                                      #
########################################################################

stoked_enabled: true

stoked_hostname: app.example.com

########################################################################
#                                                                      #
# /stoked                                                              #
#                                                                      #
########################################################################
```

Stoked is hosted on the bare hostname (it is not designed to run under a sub-path), so give it a dedicated domain.

### Secrets

The SGC `group_vars/mash_servers` layer derives all per-instance secrets from the host's master secret `sgc_pgsk`, so nothing extra needs to be set:

- RabbitMQ and MinIO credentials — `password_hash(...) | to_uuid`
- Files encryption key (`stoked_files_encryption_key`) — `sha256 | b64encode`
- LiveKit API key/secret (`stoked_livekit_key` / `stoked_livekit_secret`)

VAPID keys for Web Push are **generated at install time** by the role and persisted to `{{ stoked_base_path }}/vapid_{private,public}_key`, so they remain stable across re-runs. You can override any of these by setting the corresponding `stoked_*` variable explicitly.

## Deployment topologies

The role currently maps **one Stoked instance to one host**: a host's `vars.yml` sets a single `stoked_hostname`, and identifiers/paths/networks are scoped by the host-level `service_id_prefix` / `service_directory_prefix` (e.g. `yo-stoked-*`, `/sgc/yo-stoked`).

- **Multiple versions on different domains, one host each** — supported today. Add a `host_vars/<host>/` directory per host, each with its own `stoked_hostname`, and deploy to each host.
- **Multiple instances on a single host (e.g. stable + staging on two domains)** — **not yet supported.** It requires *variable separation per instance* so that identifiers, base paths, container networks, host ports (14702-14706, 5000, 7880/7881, the LiveKit UDP range) and Traefik routers do not collide. This is a planned role refactor (an instance-scoped variable namespace / instance loop) rather than something achievable purely from host vars.

## Usage

After running the installation, the Stoked instance becomes available at the URL specified with `stoked_hostname` (e.g. `https://app.example.com`). Open it in a browser to create the first account.

```bash
# Whole host
just install-all

# Just this service
just setup-service stoked
```

## Troubleshooting

Check the per-component systemd units and logs on the host (identifiers are host-prefixed):

```bash
systemctl list-units 'sgc-stoked-*'        # or 'yo-stoked-*' on the yo.yeet.fm host
journalctl -fu <prefix>-stoked-api.service
```

Common checks:

- **Nothing on the domain** — confirm Traefik owns `:443` on the host and that the `*-stoked-web` router (catch-all) is up; the web client is `priority: 1` so path routers win over it.
- **Voice not connecting** — verify the LiveKit RTC ports are open in the cloud firewall (see Dependencies).
- **Uploads failing** — check the `*-stoked-createbuckets` one-shot succeeded and MinIO is healthy.

## Related services

- [Traefik](traefik.md) — reverse-proxy that terminates TLS and routes all public Stoked components
