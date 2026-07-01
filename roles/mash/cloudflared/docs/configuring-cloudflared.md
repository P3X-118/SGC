<!--
SPDX-FileCopyrightText: 2026 SGC project contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Configuring Cloudflared (Cloudflare Tunnel)

This role runs a **remotely-managed** Cloudflare Tunnel connector. Most configuration lives in the Cloudflare Zero Trust dashboard; the role only needs the connector token and the standard SGC service plumbing.

## 1. Create the tunnel (Cloudflare Zero Trust dashboard)

1. Zero Trust → **Networks → Tunnels → Create a tunnel** → type **Cloudflared**.
2. Name it (e.g. `caddy-courses`) and copy the **connector token** it shows.
3. Under **Public Hostnames**, add one route per hostname you want to expose, each pointing at this host's Traefik `web` entrypoint:
   - `caddy.courses` → `HTTP` → `localhost:80`
   - `auth.caddy.courses` → `HTTP` → `localhost:80`
   - `api.caddy.courses` → `HTTP` → `localhost:80`

   Cloudflare creates the proxied `CNAME` records automatically and terminates TLS at its edge (Universal SSL covers these single-level hostnames). Traefik then routes by `Host` label to the right backend.

## 2. Provide the token to the role

Store the connector token in the host's vault and reference it:

```yaml
# inventory/host_vars/<host>/vault.yml
vault_cloudflare_tunnel_token: "<connector token from the dashboard>"
```

```yaml
# inventory/host_vars/<host>/vars.yml
cloudflared_enabled: true
cloudflared_environment_variable_tunnel_token: "{{ vault_cloudflare_tunnel_token }}"
```

`cloudflared_uid` / `cloudflared_gid` are supplied by the SGC playbook base (as for other services).

## 3. Origin: keep Traefik HTTP-only

Because Cloudflare terminates TLS at the edge, the host's Traefik needs no public certificate. On the origin host, run Traefik on the plain-HTTP `web` entrypoint and disable the `web-secure` entrypoint + ACME:

```yaml
traefik_config_entrypoint_web_enabled: true
traefik_config_entrypoint_web_secure_enabled: false
traefik_config_entrypoint_web_to_web_secure_redirect_enabled: false
traefik_config_certificatesResolvers_acme_enabled: false
```

With `web-secure` disabled, `traefik_entrypoint_primary` resolves to `web` and `traefik_certResolver_primary` resolves to empty, so services route over HTTP with no per-service label changes.

## Notes

- The connector makes only **outbound** connections — no inbound ports, no port-forwarding, no public IP required.
- This is **remotely-managed**: do not add a local `config.yml` / `credentials.json`; the token pulls all routing from the dashboard.
- The Cloudflare **DNS API token is not used** by this role (there is no DNS-01 challenge here).
