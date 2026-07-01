<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Cloudflared (Cloudflare Tunnel)

The playbook can install and configure [`cloudflared`](https://github.com/cloudflare/cloudflared) — the [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) connector — for you.

It provides **public ingress for a host with no public IP and no inbound reachability** (e.g. a residential KVM guest): `cloudflared` dials *outbound* to Cloudflare's edge, Cloudflare terminates TLS at the edge, and traffic is forwarded back through the tunnel to a local origin — typically this host's Traefik `web` (HTTP) entrypoint. This role runs a **remotely-managed** tunnel: it authenticates with a connector token and pulls its public-hostname routing from the Cloudflare Zero Trust dashboard.

> Local-only role (not published to GitHub) at `roles/mash/cloudflared/`, synced from `~/sgc/ansible/roles/cloudflared-ar/`. This is net-new edge infra for the ecosystem (closest precedent: `container-images/docker-chisel`).

For details about configuring the role, see:
- 📁 `roles/mash/cloudflared/docs/configuring-cloudflared.md` locally
- 📁 `roles/mash/cloudflared/defaults/main.yml` for the full list of options

## Dependencies

- No Traefik/Postgres dependency. It runs with **host networking** and forwards to the host's Traefik `web` entrypoint (if present). It only needs outbound network access.

## Usage

Create the tunnel in the Cloudflare Zero Trust dashboard, store its connector token in the host's vault, and enable per-host:

```yaml
# host_vars/<host>/vault.yml
vault_cloudflare_tunnel_token: "<connector token>"

# host_vars/<host>/vars.yml
cloudflared_enabled: true
cloudflared_environment_variable_tunnel_token: "{{ vault_cloudflare_tunnel_token }}"
```

Then deploy with `just setup-service cloudflared --limit <host>` from `SGC/`. Point the tunnel's public hostnames at `http://localhost:80` in the dashboard.
