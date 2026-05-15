# pds-signup

Marketing-facing signup funnel for **bskypds.pro**. Sibling to `pds-pro-ar` (operator admin panel) and `pds-ar` (per-tenant PDS instance).

## Minimum required vars

```yaml
pds_signup_enabled: true
pds_signup_hostname: "bskypds.pro"
# pds_signup_database_hostname is auto-set from postgres role when enabled.
```

That's enough for the `/healthz` endpoint to come up. Everything else (OAuth providers, Stripe/Paddle, Cloudflare DNS, affiliate registrar) is opt-in per-provider via `pds_signup_oauth_<provider>_enabled` / `pds_signup_billing_provider` / etc.

## Postgres dependency

When `postgres_enabled` is true on the same host, the database hostname / port are inherited automatically. The role appends an entry to `postgres_autom_itemized` in `group_vars/mash_servers` so Postgres provisions the database + role + password on first apply.

## Production knob walkthrough

1. **Hostname + Traefik routing.** `pds_signup_hostname` sets the public-facing host (`bskypds.pro`). Traefik routes via `Host(<hostname>)` and acquires a cert via the configured `traefik_certResolver_primary`.

2. **Session secret.** Derived from `sgc_pgsk` (`pds-signup.session` salt). Written to `state/session-secret` with mode 0600. Stable across reinstalls — no session invalidation on routine redeploys.

3. **OAuth providers.** Set `pds_signup_oauth_<provider>_enabled: true` plus the matching `client_id` / `client_secret`. Client IDs are public (rendered into config.yaml); client secrets are written to `secrets/<provider>-client-secret` mode 0600. Apple uses a private key file instead of a client secret.

4. **Billing.** Pick `pds_signup_billing_provider: "stripe"` or `"paddle"`. The corresponding API keys live in ansible-vault. Webhook secrets are written under `secrets/` mode 0600.

5. **Provisioning handoff.** `pds_signup_provisioning_runner_url` points at the AWX job template / ansible runner that consumes the handoff payload. HMAC secret derives from `sgc_pgsk` and signs every outbound webhook.

6. **Cloudflare integration.** `pds_signup_cloudflare_api_token` is scoped Zone:DNS:Edit + Zone:Zone:Read for the `bskypds.pro` zone only. Used for DNS-01 ACME (wildcard) and per-tenant `<client_slug>.bskypds.pro` record creation. Lives in ansible-vault — never in plain host_vars.

7. **Affiliate registrar.** Porkbun first; set `pds_signup_affiliate_porkbun_enabled: true` plus API keys + referral ID. Customers buy directly from the registrar via affiliate URL; commission attributed in `domain_purchase` table.

## Files written on the host

```
{{ pds_signup_base_path }}/
├── etc/
│   ├── config.yaml           # rendered, 0640
│   └── secrets/              # mode 0700
│       ├── database-url
│       ├── provisioning-hmac-secret
│       ├── google-client-secret      (if google enabled)
│       ├── stripe-secret-key         (if stripe billing)
│       ├── stripe-webhook-secret
│       └── cloudflare-api-token      (if set)
└── state/                    # mode 0750
    └── session-secret        # 0600
```
