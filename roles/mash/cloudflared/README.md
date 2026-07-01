<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Cloudflared (Cloudflare Tunnel) Ansible role

This is an [Ansible](https://www.ansible.com/) role which installs [`cloudflared`](https://github.com/cloudflare/cloudflared) — the [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) connector — to run as a [Docker](https://www.docker.com/) container wrapped in a systemd service.

It provides **public ingress for a host that has no public IP and no inbound reachability** (e.g. a residential KVM guest): `cloudflared` dials *outbound* to Cloudflare's edge, Cloudflare terminates TLS at the edge, and traffic is forwarded back through the tunnel to a local origin (typically this host's Traefik `web` entrypoint on port `80`).

This role runs a **remotely-managed** tunnel: it authenticates with a connector token (`TUNNEL_TOKEN`) and pulls its full ingress/public-hostname configuration from the Cloudflare Zero Trust dashboard. There is therefore **no local ingress config file** and **no Cloudflare DNS API token** on the host — the proxied `CNAME`s are created in the dashboard alongside the tunnel.

This role *implicitly* depends on:

- [`playbook_help`](https://github.com/P3X-118/playbook_help)
- [`systemd_docker_base`](https://github.com/P3X-118/systemd_docker_base)

Check [`defaults/main.yml`](defaults/main.yml) for the full list of supported options. Refer to [this page](docs/configuring-cloudflared.md) for details about setting up the service with this role.

## Networking

The container runs with **host networking** (`--network=host`) so a dashboard origin such as `http://localhost:80` reaches the host's Traefik `web` entrypoint. Because the connector only makes outbound connections, no ports are published and no firewall/port-forward changes are needed.

## Release model

Like other SGC roles, this role follows the 3-branch model (`main` / `sgc-dev` / `sgc`) and production releases on `sgc` are tagged by appending an incrementing `-N` suffix to the upstream `cloudflared` version (e.g. `2025.2.0-0`). The pinned `cloudflared_version` in [`defaults/main.yml`](defaults/main.yml) should be bumped to a current release before deploying.

## Development

You can optionally install [pre-commit](https://pre-commit.com/) so that simple mistakes are checked and noticed before changes are pushed to a remote branch. See [`.pre-commit-config.yaml`](./.pre-commit-config.yaml) for which hooks are to be executed.
