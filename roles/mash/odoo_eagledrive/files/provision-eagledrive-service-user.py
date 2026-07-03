# SGC: provision the `eagledrive-service` Odoo user the eagledrive scrapers'
# odoo-sync job authenticates as over JSON-RPC (vendor dossiers -> res.partner
# business profiles, one-way mirror). Contacts manager, default company =
# Eagledrive Live. Login + password are stable across runs (the scrapers VM
# carries the same derived password in its .env); a content-marker in
# ir.config_parameter gates whether the password is actually re-written, so
# unchanged re-runs are DB no-ops.
#
# Mirrors odoo_texasmodern/provision-texasmodern-service-user.py. One-shot
# `odoo-bin shell --no-http` (own DB session; coexists with running Odoo).

import hashlib
import os

LOGIN = os.environ["EAGLEDRIVE_SERVICE_LOGIN"]
NAME = os.environ["EAGLEDRIVE_SERVICE_NAME"]
COMPANY_NAME = os.environ["EAGLEDRIVE_COMPANY_NAME"]
GROUP_XMLIDS = [x for x in os.environ.get("EAGLEDRIVE_SERVICE_GROUPS", "").split(",") if x]
password = os.environ["EAGLEDRIVE_SERVICE_PASSWORD"]

# Marker fingerprints the password without storing cleartext (stable salt).
password_marker = hashlib.sha256(("eagledrive-service." + password).encode("utf-8")).hexdigest()

ICP = env["ir.config_parameter"].sudo()
existing_marker = ICP.get_param("eagledrive.service_user_password_marker") or ""

company = env["res.company"].sudo().search([("name", "=", COMPANY_NAME)], limit=1)
if not company:
    raise SystemExit(f"ERROR company {COMPANY_NAME!r} not found — run odoo_sgc_companies first")

# Resolve groups defensively (skip any xmlid missing on this edition).
groups = []
for xmlid in GROUP_XMLIDS:
    try:
        groups.append(env.ref(xmlid))
    except ValueError:
        pass
group_ids = [g.id for g in groups]

User = env["res.users"].sudo()
user = User.with_context(active_test=False).search([("login", "=", LOGIN)], limit=1)

user_created = False
password_set = False
reactivated = False

if not user:
    user = User.create({
        "login": LOGIN,
        "name": NAME,
        "password": password,
        "active": True,
        "company_id": company.id,
        "company_ids": [(6, 0, [company.id])],
        "group_ids": [(6, 0, group_ids)],
    })
    user_created = True
    ICP.set_param("eagledrive.service_user_password_marker", password_marker)
    password_set = True
else:
    if not user.active:
        user.active = True
        reactivated = True
    if existing_marker != password_marker:
        user.write({"password": password})
        ICP.set_param("eagledrive.service_user_password_marker", password_marker)
        password_set = True
    # Ensure company access + default company + group membership.
    if company.id not in user.company_ids.ids:
        user.company_ids = [(4, company.id)]
    if user.company_id.id != company.id:
        user.company_id = company.id
    for gid in group_ids:
        if gid not in user.group_ids.ids:
            user.group_ids = [(4, gid)]

env.cr.commit()

changed = user_created or password_set or reactivated
print(
    "OK"
    f" login={LOGIN}"
    f" company_id={company.id}"
    f" created={user_created}"
    f" reactivated={reactivated}"
    f" password_set={password_set}"
    f" changed={changed}"
)
