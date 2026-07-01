# `mash/minio` — SGC role: MinIO (S3-compatible object storage)

Single-node MinIO behind Traefik. Bootstraps buckets / policies / users
via `mc` post-startup. Used as the byte store for vendor photos,
menu images, and OG-image cache across SGC apps.

## What you get

- Container `{{ minio_instance }}` (default `sgc-minio`) running
  `minio/minio:RELEASE.*`.
- Data at `{{ minio_data_path }}` (default `/minio/sgc-minio/data`) —
  the only path that **must** persist across container removals.
- Public S3 endpoint at `https://{{ minio_hostname }}` (default
  `s3.sgc.ai`) via Traefik on the `traefik` network.
- Admin console at `https://{{ minio_console_hostname }}` (default
  `minio-console.sgc.ai`).
- Buckets / policies / users from `minio_buckets`,
  `minio_inline_policies`, `minio_users` — all idempotent.

## Wire-in

1. `requirements.yml` — nothing to add (custom role under `roles/mash/`).
2. `setup.yml` — append the `# role-specific:minio` block (see SGC docs).
3. `group_vars/mash_servers` — flip `minio_enabled` on the target host
   and supply `minio_root_user` / `minio_root_password` (vaulted).
4. Run `just install-service minio` then `just setup-service minio`.

## Caveats

- **Root credentials are NEVER defaulted.** `validate_config.yml` refuses
  to install if `minio_root_password` is empty or under 12 chars.
- **The `traefik` docker network must already exist on the host** (the
  Traefik role provisions it). The role asserts this and fails early
  if missing.
- **`recreate: true`** — the container is rebuilt every install run so
  env / label drift is corrected. State lives on disk, not in the
  container, so this is safe.
- **Bucket-policy values** match `mc anonymous set`:
  `public` (RW anon), `download` (read-only anon), `upload`
  (write-only anon), `none` (private). For vendor photos use `download`.
- **User-key rotation:** `mc admin user add` overwrites the secret —
  so changing `secret_key` in group_vars and re-running the role
  rotates the key. Old keys are invalidated immediately.
