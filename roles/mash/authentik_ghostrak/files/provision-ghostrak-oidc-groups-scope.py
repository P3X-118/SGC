# SGC: OIDC `groups` claim mapping for ghostrak-consuming OAuth2 providers.
#
# Ensures the named OAuth2Providers (ghostrak, prime, …) carry a `groups` JWT
# claim of the user's Authentik group names — the foundation that makes the
# ghostrak BFF + Odoo two-tier authz work without hitting the admin API on the
# hot path.
#
# CONVERGES ON THE SHARED MAPPING. Authentik does not make scope_name unique,
# so this role previously maintained its OWN row ("ghostrak: groups scope")
# with scope_name="groups" — while every per-app provisioner (provision-<app>.py)
# maintains a *different* row named "oidc groups", also scope_name="groups".
# Two rows with the same scope_name made `update_or_create(scope_name="groups")`
# in every per-app script raise MultipleObjectsReturned (a production-blocking
# provisioning crash). So this role now ATTACHES the shared "oidc groups" mapping
# instead of creating a competing one. It is attach-only: the mapping's
# expression/description are owned by the per-app provisioners, so we never
# rewrite them (that would fight those scripts and churn `changed`). We create
# the shared row — matching the per-app definition exactly — only if no per-app
# script has run yet.
#
# Idempotent. Re-runs on a steady state report `mapping=unchanged attached=[]
# changed=False` (the ansible role's changed_when reads `changed=True/False`).
#
# Run via mash/authentik_ghostrak role — sets GHOSTRAK_GROUPS_SCOPE_NAME +
# GHOSTRAK_OIDC_PROVIDERS, pipes this script through `docker exec ... ak shell`.

import os

from authentik.providers.oauth2.models import OAuth2Provider, ScopeMapping

SCOPE_NAME = os.environ.get("GHOSTRAK_GROUPS_SCOPE_NAME", "groups").strip() or "groups"

# The shared mapping owned by the per-app provisioners. Name + definition MUST
# match provision-<app>.py so a create-if-missing here is indistinguishable from
# one they would make (no churn when they later run).
SHARED_NAME = "oidc groups"
SHARED_DESCRIPTION = "group names for OIDC clients (shared SGC RBAC)"
SHARED_EXPRESSION = "return {'groups': [g.name for g in request.user.ak_groups.all()]}"

PROVIDERS = [
    p.strip()
    for p in os.environ.get("GHOSTRAK_OIDC_PROVIDERS", "ghostrak,prime").split(",")
    if p.strip()
]

# Find the shared mapping by its (scope_name, name) identity. Attach-only when it
# exists; create it (matching the per-app definition) only if nothing has yet.
mapping = ScopeMapping.objects.filter(scope_name=SCOPE_NAME, name=SHARED_NAME).first()
if mapping is None:
    mapping = ScopeMapping.objects.create(
        name=SHARED_NAME,
        scope_name=SCOPE_NAME,
        description=SHARED_DESCRIPTION,
        expression=SHARED_EXPRESSION,
    )
    mapping_status = "created"
else:
    mapping_status = "unchanged"  # shared row; owned by the per-app provisioners

# Attach to each named provider, tolerating providers that don't exist yet
# (the role might run before all OIDC providers are provisioned).
attached = []
already = []
missing = []
for name in PROVIDERS:
    provider = (
        OAuth2Provider.objects.filter(name__iexact=name).first()
        or OAuth2Provider.objects.filter(client_id__iexact=name).first()
    )
    if provider is None:
        missing.append(name)
        continue
    if provider.property_mappings.filter(pk=mapping.pk).exists():
        already.append(name)
    else:
        provider.property_mappings.add(mapping)
        attached.append(name)

changed = mapping_status != "unchanged" or bool(attached)
print(
    f"OK mapping={mapping_status} name={SHARED_NAME!r} scope_name={SCOPE_NAME} "
    f"attached={attached} already={already} missing={missing} changed={changed}"
)
