<!--
SPDX-FileCopyrightText: 2026 Oneill (SGC)
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# do-ar — Odoo (ERP) Ansible role for SGC

Deploys [Odoo](https://www.odoo.com) as a Docker container managed by systemd,
following the SGC/MASH role conventions. It runs the **custom `sgc-do` image**
built from the SGC Odoo fork (`P3X-118/do`, branch `sgc`) — see
`apps/do/sgc/docker/Dockerfile` in that repo.

This role is SGC-native: no upstream MASH/Odoo role existed, so it was built from
scratch on the same patterns as the other `*-ar` roles. It is wired into the main
SGC playbook (`SGC/`) like every other service; see `docs/configuring-do.md`.

## What it does

- Renders `odoo.conf`, an `env` file, and Traefik `labels` into `do_base_path`.
- Pulls `sgc-do:<tag>` (or builds it from the fork when
  `do_container_image_self_build: true`).
- Creates the container network and a systemd unit that runs the container.
- Publishes two Traefik routers: the main app on **8069** and the
  websocket/longpolling endpoint (`/websocket`) on **8072**.

## Requirements

- PostgreSQL 13+ (the SGC `postgres` role).
- A reverse proxy (the SGC `traefik` role).
- The MASH `systemd_docker_base` / `systemd_service_manager` roles (provided by
  the playbook), which supply the `sysd_docker_*` variables this role relies on.

## Key variables

See `defaults/main.yml`. The essentials: `do_enabled`, `do_hostname`,
`do_uid`/`do_gid`, `do_config_admin_passwd` (master password), `do_database_*`,
and `do_container_image` / `do_image_release`.

## License

AGPL-3.0-or-later. Role structure adapted from the MASH project's roles.
