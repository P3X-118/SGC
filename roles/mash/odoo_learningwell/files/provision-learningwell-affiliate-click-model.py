# odoo_learningwell — provision the x_lw_affiliate_click MANUAL model + grant the
# service user access. Records affiliate Amazon hand-offs (clicks) written by the
# Learning Well app (POST /api/affiliate/track), with conversion-ready fields
# (x_order_ref / x_revenue_cents / x_commission_cents / x_status) filled later by
# an Amazon Associates earnings import. Idempotent (find-or-create). Run via the
# one-shot `odoo-bin shell --no-http` docker run.
#
# NOTE (manual model registry reload): the running Odoo must reload its registry
# before the app can write to this model. The role runs this step BEFORE the
# module-install (which restarts Odoo), so the restart picks it up. If you run
# with install_modules=false (modules already present), restart the do service
# once after this so x_lw_affiliate_click is loaded.
#
# VALIDATE against the live Odoo 19 on first run — manual ir.model creation is
# version-sensitive; if it misbehaves, graduate to a proper custom addon.

MODEL = "x_lw_affiliate_click"

IrModel = env["ir.model"].sudo()
IrField = env["ir.model.fields"].sudo()
IrAccess = env["ir.model.access"].sudo()

changed = False

model = IrModel.search([("model", "=", MODEL)], limit=1)
if not model:
    model = IrModel.create({"name": "Affiliate Click", "model": MODEL, "state": "manual"})
    changed = True

# (name, type, label) — manual fields must be x_-prefixed.
FIELDS = [
    ("x_name", "char", "Name"),
    ("x_asins", "text", "ASINs"),
    ("x_count", "integer", "Item Count"),
    ("x_campus", "char", "Campus"),
    ("x_grade", "char", "Grade"),
    ("x_source", "char", "Source"),
    ("x_order_ref", "char", "Order Ref"),
    ("x_revenue_cents", "integer", "Revenue (cents)"),
    ("x_commission_cents", "integer", "Commission (cents)"),
    ("x_status", "char", "Status"),
]
for fname, ttype, label in FIELDS:
    if not IrField.search([("model", "=", MODEL), ("name", "=", fname)], limit=1):
        IrField.create(
            {
                "model_id": model.id,
                "name": fname,
                "field_description": label,
                "ttype": ttype,
                "state": "manual",
            }
        )
        changed = True

# Internal users (incl. learningwell-service) can read/write/create; no unlink.
grp = env.ref("base.group_user", raise_if_not_found=False)
if grp and not IrAccess.search([("model_id", "=", model.id), ("group_id", "=", grp.id)], limit=1):
    IrAccess.create(
        {
            "name": "x_lw_affiliate_click_user",
            "model_id": model.id,
            "group_id": grp.id,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": False,
        }
    )
    changed = True

env.cr.commit()
print(f"OK {MODEL} changed={changed}")
