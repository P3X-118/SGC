# pds-signup

Marketing-facing signup funnel for `bskypds.pro`. Mints customer workspaces, takes payment, optionally verifies a custom domain, and hands off a provisioning payload to the ansible runner that spins up the customer's per-tenant PDS instance.

Sibling services in this playbook:
- `pds-pro` — operator admin panel that customers land in after signup (`admin.bskypds.pro`).
- `pds` — per-tenant PDS instance (one per customer).

## Production deploy: `bskypds.pro` on `169.254.0.127`

The host `169.254.0.127` (ssh user `ronon`, key `~/.ssh/rononfps`) currently runs `awx`, `links.legit.services`, `couch.yeet.fm`, `irc.yeet.fm`, `draw.sgc.ai`, `meet.sgc.ai`, `ntfy.sgc.ai`, `work.sgc.ai`, and `noise.padge.pics`. We co-tenant `bskypds.pro` on the same host.

### 1. Add inventory entry

Add to `inventory/hosts` under `[mash_servers]`:

```
bskypds.pro ansible_host=169.254.0.127 ansible_ssh_user=ronon ansible_ssh_private_key_file=~/.ssh/rononfps ansible_python_interpreter=/bin/python3
```

### 2. Create `inventory/host_vars/bskypds.pro/vars.yml`

```yaml
rev_proxy_type: other-traefik-container

revproxy_service_networks: traefik
sgc_playbook_identifier: bskypds-pro

service_directory_prefix: "sgc-"
service_id_prefix: "sgc-"

# sgc_pgsk MUST match the value used by other services on this host or
# derived passwords won't match between deployments. Live in ansible-vault,
# not plain vars.yml — see `inventory/host_vars/bskypds.pro/vault.yml`.
# sgc_pgsk: "{{ vault_sgc_pgsk }}"

##################
# Postgres
postgres_enabled: true
postgres_connection_password: "{{ vault_postgres_connection_password }}"

##################
# pds-signup (apex bskypds.pro)
pds_signup_enabled: true
pds_signup_hostname: "bskypds.pro"
pds_signup_pds_host_a_record: "<PUBLIC-IP-OR-CHISEL-EGRESS-FOR-169.254.0.127>"

# OAuth — wire one provider for day-one (Google is fastest to set up).
pds_signup_oauth_google_enabled: true
pds_signup_oauth_google_client_id: "{{ vault_pds_signup_oauth_google_client_id }}"
pds_signup_oauth_google_client_secret: "{{ vault_pds_signup_oauth_google_client_secret }}"

# Billing — Stripe in test mode initially.
pds_signup_billing_provider: "stripe"
pds_signup_billing_stripe_publishable_key: "pk_test_..."
pds_signup_billing_stripe_secret_key: "{{ vault_pds_signup_stripe_secret_key }}"
pds_signup_billing_stripe_webhook_secret: "{{ vault_pds_signup_stripe_webhook_secret }}"

# Cloudflare — for DNS-01 ACME and per-tenant DNS record creation.
pds_signup_cloudflare_api_token: "{{ vault_pds_signup_cloudflare_api_token }}"
pds_signup_cloudflare_zone_id: "{{ vault_pds_signup_cloudflare_zone_id }}"

##################
# pds-pro (admin.bskypds.pro)
pds_pro_enabled: true
pds_pro_hostname: "admin.bskypds.pro"
pds_pro_oauth_google_enabled: true
pds_pro_oauth_google_client_id: "{{ vault_pds_pro_oauth_google_client_id }}"
pds_pro_oauth_google_client_secret: "{{ vault_pds_pro_oauth_google_client_secret }}"
pds_pro_allowlist:
  - email_domain: "sgc.ai"
    roles: ["operator"]
pds_pro_instances: []   # populated as customer PDS instances come online
```

### 3. Create `inventory/host_vars/bskypds.pro/vault.yml` (ansible-vault encrypted)

```yaml
# Encrypt with: ansible-vault encrypt inventory/host_vars/bskypds.pro/vault.yml
vault_sgc_pgsk: "..."                                  # match the value used by sibling services
vault_postgres_connection_password: "..."              # generate with `pwgen -s 64 1`
vault_pds_signup_oauth_google_client_id: "..."        # from Google Cloud Console
vault_pds_signup_oauth_google_client_secret: "..."
vault_pds_signup_stripe_secret_key: "sk_test_..."
vault_pds_signup_stripe_webhook_secret: "whsec_..."
vault_pds_signup_cloudflare_api_token: "..."          # ROTATED token, scoped Zone:DNS:Edit + Zone:Zone:Read
vault_pds_signup_cloudflare_zone_id: "..."            # bskypds.pro zone ID from CF dashboard
vault_pds_pro_oauth_google_client_id: "..."
vault_pds_pro_oauth_google_client_secret: "..."
```

### 4. Cloudflare DNS records

Create at Cloudflare dashboard for the `bskypds.pro` zone. **Proxy mode matters** — see CLAUDE.md for why customer subdomains must stay grey-cloud.

| Type | Name | Content | Proxy |
|---|---|---|---|
| A | `bskypds.pro` (apex) | `<host public IP>` | **Proxied** (orange) |
| A | `admin.bskypds.pro` | `<host public IP>` | **Proxied** (orange) |
| A | `*.bskypds.pro` (wildcard) | `<host public IP>` | **DNS-only** (grey) |
| TXT | `_acme-challenge.bskypds.pro` | (auto-managed by ACME-DNS-01 client) | DNS-only |
| MX | `bskypds.pro` | (Cloudflare Email Routing — set up in CF dashboard) | n/a |

Notes:
- The "host public IP" is what `169.254.0.127` egresses through. If you use `docker-chisel` or a similar tunnel, point at the chisel exit's public IP; if there's a public IP directly attached, use that.
- API token scope: `Zone:Zone:Read` + `Zone:DNS:Edit` for the `bskypds.pro` zone only — never a global account API key.

### 5. Build and push the container image

Per the SGC convention (build locally, push to Docker Hub):

```bash
cd ~/sgc/apps/pds-signup
just image v0.1.0
# → docker.io/legitservices/pds-signup:v0.1.0
```

Then update `pds_signup_container_image` in vars.yml to that tag.

### 6. Publish the ansible role

The role lives locally at `~/sgc/ansible/roles/pds-signup-ar/` but isn't on GitHub yet. The `requirements.yml` entry is **commented out** for that reason. To activate:

```bash
# 1. Create + push the role repo (gated to user — DO NOT auto-push)
cd ~/sgc/ansible/roles/pds-signup-ar
git init -b main
git add . && git commit -m "Initial pds-signup-ar role"
gh repo create P3X-118/pds-signup-ar --private --source=. --push
git checkout -b sgc && git push -u origin sgc

# 2. Uncomment the entry in ~/sgc/SGC/requirements.yml (the # role-specific:pds_signup block)

# 3. Fetch into the playbook
cd ~/sgc/SGC
just roles
```

### 7. Apply the playbook

```bash
cd ~/sgc/SGC

# Smoke-test the variables / template rendering for this host first
ansible-inventory --host bskypds.pro --vault-password-file ~/.vault-password

# Dry run
just install-service pds_signup --check --diff

# Apply
just install-service pds_signup
just install-service pds_pro
```

### 8. Verify

```bash
# DNS resolves
dig bskypds.pro +short

# TLS cert is live (Traefik/Caddy provisioned via ACME)
curl -sI https://bskypds.pro/healthz
# → HTTP/2 200, content-type: application/json

# Apex landing renders
curl -s https://bskypds.pro/ | head -5

# Sign-in page lists Google
curl -s https://bskypds.pro/signup | grep -i 'continue with google'
```

## Known gaps (filling in as we go)

- **`sgc-secret-resolver`** — the centralized secret-derivation service (Go + mTLS, only process besides ansible holding `sgc_pgsk`) is referenced in the architectural design but not yet built. PDS-Pro currently reads per-instance admin passwords from per-tenant secret files written by ansible directly. Promote to the resolver model when one of:
  - The number of tenants grows past ~50 (per-file becomes unwieldy)
  - PDS-Pro needs to derive secrets dynamically (e.g., for a tenant created via the UI, not via ansible)
  - Compliance requires `sgc_pgsk` to live in only one process

- **AWX provisioning runner** — `pds_signup_provisioning_runner_url` is empty. Until wired, signup completes through workspace + payment but provisioning is manual. To wire: create an AWX job template that runs the `pds-ar` role with the handoff payload as extra-vars, then set `pds_signup_provisioning_runner_url` to its launch URL.

- **OAuth providers beyond Google** — Apple, Microsoft, Meta, X, TikTok credentials need to be obtained from each provider's developer portal. Add to vault as they come online.

- **Apex landing copy** — current text is functional but unreviewed by marketing. Edit `~/sgc/apps/pds-signup/web/templates/index.html` and rebuild the image.

- **Reserved-slug list** — currently 26 entries; expand as you discover collisions / abuse vectors.

- **Schema migration runner** — `migrations/001_initial.up.sql` exists but is run manually via `just migrate "$DATABASE_URL"`. A baked-in migrator (golang-migrate or similar) would let the container apply migrations on startup. Worth adding before second migration.

## Rollback

```bash
# Stop the service on the host
ssh ronon@169.254.0.127 sudo systemctl stop sgc-pds-signup

# Or remove from inventory and re-apply:
# (edit host_vars/bskypds.pro/vars.yml: pds_signup_enabled: false)
just install-service pds_signup
```

The Postgres database persists; data isn't lost on rollback. To fully wipe:

```bash
ssh ronon@169.254.0.127 sudo rm -rf /sgc/sgc-pds-signup
# + drop the postgres database manually
```
