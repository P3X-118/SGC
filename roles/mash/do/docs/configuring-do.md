<!--
SPDX-FileCopyrightText: 2026 Oneill (SGC)
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Configuring Odoo (do)

Enable Odoo by adding the following to your SGC `vars.yml`. The playbook already
derives `do_uid`/`do_gid`, the database credentials, the master password, and the
Traefik settings, so you normally only set the hostname and turn it on:

```yaml
do_enabled: true
do_hostname: odoo.example.com
```

## First run: create the database

The deployment ships with `list_db = False` and a strict `dbfilter`, so the web
database manager is locked down. Initialise the (pre-created, empty) PostgreSQL
database once:

```bash
docker exec -it sgc-do odoo-bin -c /etc/odoo/odoo.conf \
  -d <db> -i base --stop-after-init --without-demo=all
```

Afterwards Odoo serves `<db>` directly (it is pinned by `dbfilter`).

## Master password

`do_config_admin_passwd` is the **master password** controlling database
create/drop/backup. In the SGC playbook it is derived from `sgc_pgsk`; never
leave it empty.

## Email

Outgoing mail is configured inside Odoo (Settings → Technical → Outgoing Mail
Servers), pointing at the SGC `exim` relay (`sgc-exim-relay:8025`). The playbook
attaches Odoo to the exim network when `exim_relay_enabled`.

## Reverse proxy / websockets

Odoo needs `/websocket` (and legacy `/longpolling`) routed to the gevent port
(8072) while everything else goes to 8069. This role emits both Traefik routers
automatically (toggle with `do_container_labels_traefik_websocket_enabled`).

## Custom addons

Set `do_extra_addons_enabled: true` and drop modules into `do_extra_addons_path`
(mounted read-only at `/mnt/extra-addons`, already on `addons_path`). For changes
to Odoo **core**, modify the fork and rebuild the image instead.

## Workers

`do_config_workers` defaults to 2. For production size it as
`(CPU cores * 2) + 1` and budget ~250 MiB RAM per worker plus the
`limit_memory_hard` headroom.
