# SGC: WRITE-capable Authentik API token for the ghostrak Odoo addon's
# coach-assignment sync (closes seam #3 of the ghostrak↔Odoo↔Authentik
# integration). The addon reads this token from ir.config_parameter at
# runtime and calls Authentik admin API to add/remove a user from
# ghostrak-coaches (or other capability groups) when their res.partner
# ghostrak_role changes in Odoo.
#
# Separate service account from svc-ghostrak-tiers (read-only) and
# svc-ghostrak-provision (write — player provisioning); each has its own
# token so they rotate / audit independently.
#
# Scope: group-membership writes ONLY. Deliberately does NOT grant add_user
# or change_user — Odoo is not allowed to create or modify Authentik users
# via this token, only assign them to / unassign them from groups.
#
# Token key supplied via env (GHOSTRAK_ODOO_TOKEN), derived in the role from
# the consumer host's sgc_pgsk so the Authentik side and the Odoo side use
# the same value without operator hand-off.
#
# Re-runnable: detects whether the service account permissions or the token
# key actually changed; reports `changed=True/False` so the ansible role's
# changed_when reads idempotent on a steady state.

import os

from django.contrib.auth.models import Permission
from authentik.core.models import Token, TokenIntents, User, UserTypes

key = os.environ["GHOSTRAK_ODOO_TOKEN"]
USERNAME = "svc-ghostrak-odoo"
SVC_NAME = "ghostrak-odoo (group-membership write service account)"
TOKEN_IDENTIFIER = "ghostrak-odoo"
TOKEN_DESCRIPTION = (
    "ghostrak Odoo addon: add/remove user from ghostrak-* capability groups "
    "on res.partner ghostrak_role write"
)
# Authentik's `POST /api/v3/core/groups/{pk}/add_user/` (and /remove_user/)
# is guarded by the CUSTOM Group permissions `add_user_to_group` /
# `remove_user_from_group` (defined in authentik.core.models.Group.Meta.
# permissions), not the standard change_group/change_user. Granting standard
# CRUD perms returns 403; those two custom codenames are the actual gate.
# (svc-ghostrak-provision, the BFF write token, doesn't hit this because it
# creates users with `groups: [...]` set at CREATE time — a different code
# path that's gated by change_user. We hit add_user_to_group/remove because
# we modify EXISTING users.)
PERM_CODENAMES = {
    "view_user",
    "view_group",
    "add_user_to_group",
    "remove_user_from_group",
}

# --- Service account: detect change before writing ------------------------
existing_svc = User.objects.filter(username=USERNAME).first()
svc_will_change = (
    existing_svc is None
    or existing_svc.name != SVC_NAME
    or not existing_svc.is_active
    or existing_svc.type != UserTypes.SERVICE_ACCOUNT
)
svc, svc_created = User.objects.update_or_create(
    username=USERNAME,
    defaults=dict(
        name=SVC_NAME,
        type=UserTypes.SERVICE_ACCOUNT,
        is_active=True,
    ),
)

# --- Permissions: only the set we need; report when something changed -----
current_perms = set(
    svc.user_permissions.filter(
        content_type__app_label="authentik_core",
        codename__in=PERM_CODENAMES,
    ).values_list("codename", flat=True)
)
missing_perms = PERM_CODENAMES - current_perms
if missing_perms:
    svc.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="authentik_core",
            codename__in=missing_perms,
        )
    )
perms_changed = bool(missing_perms)

# --- Token: only consider "changed" when the KEY actually differs ---------
existing_token = Token.objects.filter(identifier=TOKEN_IDENTIFIER).first()
token_key_changed = existing_token is None or existing_token.key != key
tok, tok_created = Token.objects.update_or_create(
    identifier=TOKEN_IDENTIFIER,
    defaults=dict(
        user=svc,
        intent=TokenIntents.INTENT_API,
        key=key,
        expiring=False,
        description=TOKEN_DESCRIPTION,
    ),
)

changed = svc_will_change or perms_changed or token_key_changed
print(
    "OK"
    f" service_account={USERNAME}({'created' if svc_created else 'updated'})"
    f" perms_added={sorted(missing_perms)}"
    f" token={TOKEN_IDENTIFIER}({'created' if tok_created else 'updated'})"
    f" key_len={len(tok.key)} changed={changed}"
)
