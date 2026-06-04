# SGC: OIDC `groups` claim mapping for ghostrak-consuming OAuth2 providers.
#
# Creates (or updates in place) a single Authentik ScopeMapping that emits the
# user's Authentik group names as a `groups` JWT claim, then attaches it to
# each of the named OAuth2Providers. After this runs, any OIDC client that
# requests `groups` in its scope parameter will see the claim in its token —
# which is the foundation that makes the ghostrak BFF + Odoo two-tier authz
# work without ever calling the Authentik admin API on the hot path.
#
# Idempotent. Re-runs report `mapping=unchanged attached=[] changed=False`
# (the ansible role's changed_when reads `changed=True/False` from this line).
#
# Run via mash/authentik_ghostrak role — sets GHOSTRAK_GROUPS_SCOPE_NAME +
# GHOSTRAK_OIDC_PROVIDERS, pipes this script through `docker exec ... ak shell`.

import os

from authentik.providers.oauth2.models import OAuth2Provider, ScopeMapping

SCOPE_NAME = os.environ.get("GHOSTRAK_GROUPS_SCOPE_NAME", "groups").strip() or "groups"
MAPPING_NAME = "ghostrak: groups scope"
DESCRIPTION = (
    "ghostrak: emit Authentik group names as the OIDC `groups` claim. "
    "Provisioned by mash/authentik_ghostrak."
)
EXPRESSION = (
    "# Emit the user's Authentik group names as a `groups` claim.\n"
    "# Managed by mash/authentik_ghostrak (provision-ghostrak-oidc-groups-scope.py).\n"
    "return {\"groups\": [group.name for group in request.user.ak_groups.all()]}\n"
)
PROVIDERS = [
    p.strip()
    for p in os.environ.get("GHOSTRAK_OIDC_PROVIDERS", "ghostrak,prime").split(",")
    if p.strip()
]

# Create-or-update the mapping. Track whether anything actually changed so the
# ansible role can report changed=False on a no-op run.
existing = ScopeMapping.objects.filter(name=MAPPING_NAME).first()
if existing is None:
    mapping = ScopeMapping.objects.create(
        name=MAPPING_NAME,
        scope_name=SCOPE_NAME,
        description=DESCRIPTION,
        expression=EXPRESSION,
    )
    mapping_status = "created"
elif (
    existing.scope_name != SCOPE_NAME
    or existing.description != DESCRIPTION
    or existing.expression != EXPRESSION
):
    existing.scope_name = SCOPE_NAME
    existing.description = DESCRIPTION
    existing.expression = EXPRESSION
    existing.save()
    mapping = existing
    mapping_status = "updated"
else:
    mapping = existing
    mapping_status = "unchanged"

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
    f"OK mapping={mapping_status} scope_name={SCOPE_NAME} "
    f"attached={attached} already={already} missing={missing} changed={changed}"
)
