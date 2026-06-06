<!--
SPDX-FileCopyrightText: 2026 SGC / P3X-118 contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# AzuraCast

The playbook can install and manage [AzuraCast](https://www.azuracast.com/) — a
free, self-hosted, all-in-one web radio management suite — via the SGC
[`azuracast-ar`](https://github.com/P3X-118/azuracast-ar) role (dev home:
`ansible/roles/azuracast-ar`).

AzuraCast ships as a **monolithic** Docker image: one container runs nginx,
PHP-FPM, MariaDB, Redis, Liquidsoap (AutoDJ), and the Icecast/Shoutcast/SFTPGo
broadcast frontends together. The role wraps that single container as a systemd
unit (devture `systemd_docker_base` pattern) and **omits** the upstream
Watchtower `updater` — image/version is owned by Ansible.

> **Status: not yet activated.** This documents the integration. The live
> station still runs hand-managed at `sonic:/home/oneill/Azura`
> (`docker.sh` + `docker-compose.yml`). Activation requires a data + edge
> migration — see the runbook below. The role and `host_vars` ship
> **disabled** (`azuracast_enabled: false`).

## Dependencies

- `systemd_docker_base` and the playbook base (implicit, as for all SGC roles).
- No shared Postgres/Redis: AzuraCast embeds its own MariaDB + Redis.

## Integration (the 4-step pattern)

> ✅ The role repo is published: **https://github.com/P3X-118/azuracast-ar**,
> tag **`v0.1.0-0`** on `sgc`. Apply step 2 (`setup.yml`) only together with a
> `just roles` run that fetches the role into `roles/galaxy/azuracast` —
> otherwise playbook parsing breaks for every host.

### 1. `requirements.yml`

```yaml
# role-specific:azuracast
- src: git+https://github.com/P3X-118/azuracast-ar.git
  version: v0.1.0-0
  name: azuracast
  activation_prefix: azuracast_
# /role-specific:azuracast
```

### 2. `setup.yml` (alphabetical)

```yaml
    # role-specific:azuracast
    - when: azuracast_enabled | bool
      role: galaxy/azuracast
    # /role-specific:azuracast
```

### 3. `group_vars/mash_servers` — itemized service list

```yaml
  # role-specific:azuracast
  - |-
    {{ ({'name': (azuracast_identifier + '.service'), 'priority': 2000, 'groups': ['sgc', 'azuracast']} if azuracast_enabled else omit) }}
  # /role-specific:azuracast
```

### 4. `group_vars/mash_servers` — service vars block (alphabetical)

```yaml
# role-specific:azuracast
########################################################################
#                                                                      #
# azuracast                                                            #
#                                                                      #
########################################################################

azuracast_enabled: false
azuracast_identifier: "{{ service_id_prefix }}azuracast"
azuracast_base_path: "{{ sgc_playbook_base_path }}/{{ service_directory_prefix }}azuracast"
azuracast_uid: "{{ sgc_playbook_uid }}"
azuracast_gid: "{{ sgc_playbook_gid }}"

# Dormant until the Caddy->Traefik edge cutover flips traefik_enabled true
# (overridden per-host; see host_vars/spin.yeet.fm).
azuracast_container_additional_networks_auto: |
  {{
    ([revproxy_service_networks] if (azuracast_container_labels_traefik_enabled | bool) and revproxy_service_networks | default('') else [])
  }}

azuracast_container_labels_traefik_docker_network: "{{ revproxy_service_networks }}"

# role-specific:traefik
azuracast_container_labels_traefik_entrypoints: "{{ traefik_entrypoint_primary }}"
azuracast_container_labels_traefik_tls_certResolver: "{{ traefik_certResolver_primary }}"
# /role-specific:traefik

########################################################################
#                                                                      #
# /azuracast                                                           #
#                                                                      #
########################################################################
# /role-specific:azuracast
```

Then add `spin.yeet.fm` to the inventory `hosts` file and run
`just install-service azuracast` / `just setup-service azuracast`.

## Host configuration

Host-specific settings (ports, image, secrets, volume adoption, edge) live in
`inventory/host_vars/spin.yeet.fm/vars.yml`. That file targets **sonic**
(`ansible_host: 10.20.0.51`, where the station physically runs) and keeps the
service disabled.

## Activation / migration runbook

The live station is fronted by **sonic's host Caddy** (`spin.yeet.fm` and
`radio.yeet.fm` → `localhost:2001`, TLS terminated at Caddy) and stores all
state in the `azuracast_*` named volumes (`COMPOSE_PROJECT_NAME=azuracast`).
Migrate carefully:

> ### 🛑 HARD GATE — no downtime without verified config-backup parity
> **Do NOT `./docker.sh down` the live station until we are certain that, on
> bring-up, it returns with the *identical* configuration.** AzuraCast keeps
> nearly all configuration in its database (stations, mount points, playlists,
> streamers/DJs, users, API keys, settings) inside the `azuracast_db_data`
> volume, plus the `azuracast.env`/`.env` runtime settings. Before any cutover:
> 1. Take a full backup and **verify it is complete and restorable**:
>    `./docker.sh backup /path/backup-$(date +%F).tar.gz` (exports DB + config + media).
> 2. Snapshot/copy the `azuracast_*` named volumes (esp. `azuracast_db_data`) and
>    the `.env` + `azuracast.env` files so the exact prior config can be restored.
> 3. Record the live settings the role must reproduce (ports 2001/4443/2022,
>    station ports, station mount points, base URL/branding) and confirm they are
>    reflected in `host_vars/spin.yeet.fm` + the role's env template.
> 4. Only proceed when a dry restore of the backup has been validated and we can
>    bring the station back up to the same state on rollback.

1. **Back up first**: `cd /home/oneill/Azura && ./docker.sh backup` — and complete the HARD GATE above.
2. **Publish the role**: create `P3X-118/azuracast-ar` (3-branch model), tag a
   release on `sgc`, then apply integration steps 1–2 and run `just roles`.
3. **Secrets**: vault the live DB credentials from `azuracast.env` as
   `vault_azuracast_mysql_password` / `vault_azuracast_mysql_root_password`.
   They must match the existing `azuracast_db_data` volume, or AzuraCast can't
   connect (the `host_vars` adopts that volume rather than starting empty).
4. **Data**: the `host_vars` mounts the existing `azuracast_*` named volumes, so
   no data copy is needed — but the hand-run container must be **stopped** so it
   releases the DB before the systemd unit starts the same volumes. Plan a
   short maintenance window: `./docker.sh down`, then enable the role.
5. **Edge (do last, separately)**: while migrating compute, keep
   `azuracast_container_labels_traefik_enabled: false` and the web ports
   host-published so Caddy keeps working unchanged. Only after the container is
   healthy under systemd, plan the Caddy → Traefik cutover: enable Traefik
   labels + attach the Traefik network for the **HTTP web UI**; the
   Icecast/Shoutcast broadcast ports (8000/8005/8006/8010) and SFTP stay
   host-published (Traefik TCP routing is a later refinement). Caddy fronts
   other production services on sonic — change one vhost at a time.
6. **Verify**: `just setup-service azuracast --tags self-check` and confirm the
   stream + control panel at `https://spin.yeet.fm`.
