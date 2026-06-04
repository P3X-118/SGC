# SGC: capability groups for ghostrak — the coarse role primitives in the JWT
# `groups` claim. Fine per-facility/per-player scope lives in Odoo's ghostrak
# addon, which syncs membership in these groups via the Authentik admin token
# whenever an assignment changes.
#
# Idempotent: get_or_create on each Group.name. Re-runs print
# `OK created=[] existed=[...]` so the ansible role's changed_when:
# "'created=[]' not in stdout" reports `changed=false` on no-op runs.
#
# Run via mash/authentik_ghostrak role (which sets CAPABILITY_GROUPS and
# does the docker exec ... ak shell < piping). Defaults match the role's
# authentik_ghostrak_capability_groups list — keep both in sync.

import os

from authentik.core.models import Group

DEFAULT = ",".join([
    "ghostrak-admins",
    "ghostrak-facility-owners",
    "ghostrak-coaches",
    "ghostrak-recruiters",
    "ghostrak-users",
])

names = [
    n.strip()
    for n in os.environ.get("CAPABILITY_GROUPS", DEFAULT).split(",")
    if n.strip()
]

created = []
existed = []

for name in names:
    _, was_created = Group.objects.get_or_create(name=name)
    (created if was_created else existed).append(name)

print(f"OK created={created} existed={existed} total={len(names)}")
