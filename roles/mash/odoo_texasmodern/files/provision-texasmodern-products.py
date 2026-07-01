# SGC: provision the Texas Modern Waste service products that intake sale.order
# lines reference (weekly trash cart service, quarterly cart cleaning, valet
# trash). Idempotent — keyed on default_code (SKU). Service-type so no stock is
# tracked. list_price defaults to 0.0 (TMW staff set real pricing in Odoo; the
# intake form carries no price). Scoped to the Texas Modern Waste company.
# One-shot `odoo-bin shell --no-http`.
#
# Mirrors odoo_learningwell/provision-learningwell-bundle-product.py, looped over
# the TMW_PRODUCTS env (JSON array of {code, name}).

import json
import os

COMPANY_NAME = os.environ["TMW_COMPANY_NAME"]
PRODUCTS = json.loads(os.environ["TMW_PRODUCTS"])  # [{"code": "...", "name": "..."}, ...]

company = env["res.company"].sudo().search([("name", "=", COMPANY_NAME)], limit=1)
if not company:
    raise SystemExit(f"ERROR company {COMPANY_NAME!r} not found — run odoo_sgc_companies first")

Product = env["product.product"].sudo()

created_codes = []
existing_codes = []
for spec in PRODUCTS:
    code = spec["code"]
    name = spec["name"]
    product = Product.search([("default_code", "=", code)], limit=1)
    if product:
        existing_codes.append(code)
        continue
    vals = {
        "name": name,
        "default_code": code,
        "type": "service",      # services are fulfilled on a route; no inventory
        "sale_ok": True,
        "purchase_ok": False,
        "list_price": 0.0,      # staff set TMW pricing in Odoo
        "company_id": company.id,
    }
    Product.create(vals)
    created_codes.append(code)

env.cr.commit()

changed = bool(created_codes)
print(
    "OK"
    f" model=product.product company_id={company.id}"
    f" created={created_codes}"
    f" existing={existing_codes}"
    f" changed={changed}"
)
