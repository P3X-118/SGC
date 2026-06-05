# SGC: provision the bff-service Odoo user that the ghostrak BFF authenticates
# as for the seam #7 authz queries. Login + password are stable across runs
# (both sides derive from prime's sgc_pgsk + '.odoo.bff'); a content-marker
# in ir.config_parameter gates whether the password is actually re-set, so
# re-runs that don't change the source secret are no-ops at the DB level.
#
# Internal user only (base.group_user). The BFF doesn't need any custom Odoo
# groups for read-only res.partner queries — the addon's custom fields live
# on res.partner which Internal Users can read by default.
#
# Run via mash/odoo_ghostrak's provision_bff_service_user concern, piped
# through `odoo shell -d <db> --no-http` in a one-shot docker run (same
# image/mounts/network as the long-running prime-do, no downtime — shell
# coexists with the running Odoo on its own DB connection).

import hashlib
import os

LOGIN = "bff-service"
NAME = "ghostrak BFF (service account)"
password = os.environ["BFF_SERVICE_PASSWORD"]

# Marker fingerprints the password without storing it in cleartext. Salt
# 'bff-service.' is constant — the marker is a stable function of the
# password value, so re-runs with the same password reproduce the same
# marker and we skip the re-write.
password_marker = hashlib.sha256(
    ("bff-service." + password).encode("utf-8")
).hexdigest()

ICP = env["ir.config_parameter"].sudo()
existing_marker = ICP.get_param("ghostrak.bff.service_user_password_marker") or ""

# Find user (include inactive in case someone disabled it manually).
User = env["res.users"].sudo()
user = User.with_context(active_test=False).search([("login", "=", LOGIN)], limit=1)

user_created = False
password_set = False
reactivated = False

internal_group = env.ref("base.group_user")

if not user:
    user = User.create({
        "login": LOGIN,
        "name": NAME,
        "password": password,
        "active": True,
        "group_ids": [(6, 0, [internal_group.id])],
    })
    user_created = True
    ICP.set_param("ghostrak.bff.service_user_password_marker", password_marker)
    password_set = True
else:
    # Reactivate if disabled.
    if not user.active:
        user.active = True
        reactivated = True
    # Only re-write the password when the source value actually changed.
    if existing_marker != password_marker:
        user.write({"password": password})
        ICP.set_param("ghostrak.bff.service_user_password_marker", password_marker)
        password_set = True
    # Ensure Internal User group membership.
    if internal_group not in user.group_ids:
        user.group_ids = [(4, internal_group.id)]

env.cr.commit()

changed = user_created or password_set or reactivated
print(
    "OK"
    f" login={LOGIN}"
    f" created={user_created}"
    f" reactivated={reactivated}"
    f" password_set={password_set}"
    f" changed={changed}"
)
