# mash/eagledrive

Deploys the `eagledrive.live` docker-compose stack (Fastify API + Postgres + Redis) onto a prod host.

External SGC services (ntfy, pds, pds-pro, changedetection, reitti, gun-relay) are **not** part of this stack — they're reached over the network and configured via the `eagledrive_*_url` variables.

## Enabling

1. In `group_vars/mash_servers` (or per-host vars), set `eagledrive_enabled: true` and provide:
   - `eagledrive_repo_url`, `eagledrive_repo_version`
   - `eagledrive_postgres_password` (vaulted)
   - All `eagledrive_*_url` endpoints pointing at the prod SGC instances
2. Add a role entry to `setup.yml`:
   ```yaml
   - when: eagledrive_enabled | bool
     role: mash/eagledrive
   ```
3. `just install-service eagledrive` (or `just setup-all`).

## Stub status

This is an initial stub. Missing pieces a future revision should add: systemd unit wrapping `docker compose`, log rotation, healthcheck reporting, backup of the `postgres-data` volume, optional Traefik/Caddy front-end.
