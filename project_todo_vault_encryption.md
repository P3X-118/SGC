<!--
SPDX-FileCopyrightText: 2026 SGC / P3X-118 contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Project TODO: ansible-vault encryption migration

**Status: in progress.** SGC is migrating per-host secrets from plaintext
`vault_*` placeholders (in the gitignored
`inventory/host_vars/<host>/{vars,vault}.yml`) to real `ansible-vault`-encrypted
values. Several host_vars comments reference this file (e.g.
`eagledrive.live`, `beege-flaresolverr`, `flareface`).

## Goal

- Configure a vault password mechanism — there is **no `vault_password_file`**
  in `ansible.cfg` yet, so encrypted files cannot be decrypted on playbook runs.
- Encrypt every `vault_*` secret file with `ansible-vault`.
- Replace the remaining plaintext `PASTE_…_HERE` placeholders with real values.

## Pending items

- [ ] **spin.yeet.fm (AzuraCast)** — `vault_azuracast_mysql_password`,
  `vault_azuracast_mysql_root_password`. Template:
  `inventory/host_vars/spin.yeet.fm/vault.yml.example`.
  ⚠️ When adopting the running station, these **must equal** the credentials
  already in the live `azuracast_db_data` volume
  (`sonic:/home/oneill/Azura/azuracast.env` → `MYSQL_PASSWORD` /
  `MYSQL_ROOT_PASSWORD`), or AzuraCast cannot connect. *(azuracast-ar migration
  step 3 — see `docs/services/azuracast.md`.)*
- [ ] **eagledrive.live** — see `inventory/host_vars/eagledrive.live/vars.yml`
  (`TODO move to ansible-vault`).
- [ ] **beege-flaresolverr** — plaintext per current SGC pattern.
- [ ] **flareface** — plaintext per current SGC pattern.

## How (per host)

```bash
cp inventory/host_vars/<host>/vault.yml.example inventory/host_vars/<host>/vault.yml
# fill in real values, then:
ansible-vault encrypt inventory/host_vars/<host>/vault.yml
# configure the vault password (vault_password_file in ansible.cfg, or --ask-vault-pass)
```
