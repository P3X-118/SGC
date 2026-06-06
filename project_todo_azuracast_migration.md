<!--
SPDX-FileCopyrightText: 2026 SGC / P3X-118 contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Project TODO: AzuraCast → SGC Ansible migration

Bring the hand-run AzuraCast deployment (`sonic:/home/oneill/Azura`, docker-compose
+ `docker.sh`) under the SGC `azuracast-ar` role. **Live station must stay up
until cutover is proven safe.** See `docs/services/azuracast.md` for the runbook.

## Done
- [x] Role `azuracast-ar` built + published — https://github.com/P3X-118/azuracast-ar
  (`main`/`sgc-dev`/`sgc`, tag `v0.1.0-0`); install-verified via `ansible-galaxy`.
- [x] 4-step wiring committed on `sgc-dev` (`40119a71`, disabled by default).
- [x] `inventory/host_vars/spin.yeet.fm/{vars.yml,vault.yml.example}` (targets sonic).
- [x] Service doc + vault TODO + cutover HARD GATE (`4a1a58f4`).

## Pending
- [ ] **Push** `40119a71` + `4a1a58f4` to `origin/sgc-dev` (coordinate with the
  in-flight seam-#7 WIP on that branch).
- [ ] **Vault DB creds** — `vault_azuracast_mysql_*` for `spin.yeet.fm`
  (see `project_todo_vault_encryption.md`). Must match the live `azuracast_db_data`.
- [ ] **Publish custom image** `legitservices/azuracast` (Docker Hub), or keep the
  upstream `ghcr.io/azuracast/azuracast` default until then.
- [ ] **Add `spin.yeet.fm` to the inventory `hosts` file** (otherwise the role
  never targets a host).
- [ ] **Data adoption dry-run** — confirm the `azuracast_*` named volumes exist and
  the role's volume mounts line up (`docker volume ls | grep azuracast_`).
- [ ] **Config-backup parity (HARD GATE)** — full `./docker.sh backup` + volume
  snapshot + validated dry restore BEFORE any `./docker.sh down`. No downtime until
  bring-up is proven to return the identical configuration.
- [ ] **Cutover** — stop the hand-run container, `azuracast_enabled: true`, run
  `just install-service azuracast` / `just setup-service azuracast`, verify
  control panel + stream at `https://spin.yeet.fm`.
- [ ] **Edge migration (LAST, separate)** — migrate `spin.yeet.fm` /
  `radio.yeet.fm` from sonic's host Caddy to the SGC Traefik pattern. Only the
  HTTP web UI routes via Traefik; Icecast/Shoutcast TCP broadcast ports + SFTP stay
  host-published. One vhost at a time — Caddy fronts other production services.
- [ ] **Decommission** the hand-run `docker.sh`/compose path once the role owns it.
