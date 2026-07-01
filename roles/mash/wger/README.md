# wger-ar

SGC Ansible role that deploys [wger](https://github.com/wger-project/wger)
(FLOSS Workout Manager) as systemd-managed Docker containers, using the
`legitservices/wger` image built from the `P3X-118/wger` source fork
(`~/sgc/apps/wger`).

Follows the SGC MASH/`sysd` pattern — `docker create` + `docker start --attach`
per systemd unit, **not** docker-compose. Architecturally a Django + PostgreSQL
+ Redis + Celery app; modelled on the multi-service `awx-ar` role and the
Django `weblate-ar` role.

## Where this role lives (local-only, no GitHub)

This directory (`ansible/roles/wger-ar/`) is the **canonical development home**,
the same convention every `-ar` role uses. wger is kept **local** — we do *not*
publish it to GitHub and fetch it into `roles/galaxy/`. Instead the playbook
consumes a committed copy at **`SGC/roles/mash/wger/`**, referenced from
`setup.yml` as `mash/wger`.

```
edit here  ->  just deploy-local  ->  SGC/roles/mash/wger  ->  playbook (mash/wger)
```

Always edit this copy, then run `just deploy-local` to sync. (When/if we later
publish to `P3X-118/wger-ar`, switch `setup.yml` from `mash/wger` to
`galaxy/wger`, add the entry to `requirements.yml`, and drop the mash copy.)

## Services (systemd units)

| Unit | Purpose | Image command |
|---|---|---|
| `wger-nginx.service` | **Traefik-facing.** Serves `/static` + `/media` from the volumes and reverse-proxies the app. Required — wger's gunicorn image serves no static/media in prod. | `nginx` |
| `wger.service` | Web (gunicorn), internal. Self-bootstraps on start: migrations, fixtures, admin user, collectstatic. | default entrypoint |
| `wger-redis.service` | Django cache + Celery broker/backend | `redis` |
| `wger-worker.service` | Celery worker — *only when `wger_celery_enabled`* | `/start-worker` |
| `wger-beat.service` | Celery beat — *only when `wger_celery_enabled`* | `/start-beat` |

Request path: **Traefik → `wger-nginx`:8080 → (`/static`,`/media` from disk | everything else → `wger`:8000 gunicorn)**. nginx runs as the wger user (uid 1000) so it reads the static/media mounts without loosening perms; all scratch is on a `/tmp` tmpfs. `wger_nginx_enabled: false` reverts to Traefik → gunicorn directly (static/media will 404 unless you provide another server).

Identifiers are prefixed per host via `service_id_prefix` (`sgc-wger`,
`training-wger`, …), so the role coexists with other aliases on a shared
Docker daemon.

## Requirements

- External **PostgreSQL** (the SGC `postgres` role). The DB is registered in
  `postgres_autom_itemized` in `group_vars/mash_servers`.
- **Traefik** for TLS termination / routing (`wger_container_labels_traefik_*`).
- The web/worker/beat containers reach Postgres and Redis via the networks
  supplied in `wger_container_additional_networks_auto` (set in group_vars).

## Key variables

See `defaults/main.yml`. Most important:

- `wger_enabled` (default `false` in the SGC group_vars), `wger_hostname`,
  `wger_site_url`, `wger_csrf_trusted_origins`
- `wger_secret_key` (derived from `sgc_pgsk` in group_vars; auto-generated if empty)
- `wger_database_*` (engine/host/port/name/user/password)
- `wger_redis_enabled` (default `true`), `wger_celery_enabled` (default `false`)
- `wger_jwt_private_key` / `wger_jwt_public_key` — optional, only for mobile/JWT
  auth; generate with `./manage.py generate-jwt-keys`
- `wger_email_*` — optional SMTP relay

## Notes

- The image's `wger` user is uid/gid **1000**; host bind-mount dirs
  (`media/`, `static/`, `beat/`) are created with that ownership.
- `wger bootstrap` ships a default `admin` / `adminadmin` account from the
  fixtures — change it after first start.
- Disabling the service (`wger_enabled: false`) removes `wger_base_path`,
  **including uploaded media** — back up first.

Part of the SGC ecosystem; see `~/sgc/CLAUDE.md` and the source fork's
`~/sgc/apps/wger/CLAUDE.md` (image build/release details).
