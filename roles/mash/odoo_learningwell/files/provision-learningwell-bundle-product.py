# SGC: provision the generic "School Supply Bundle" product that The Learning
# Well sale.order lines reference (until per-(school, grade) products exist).
# Idempotent — keyed on default_code (SKU). Service-type so no stock is tracked;
# taxes cleared so the line price stays the final price already charged via
# Stripe. Scoped to the managed company. One-shot `odoo-bin shell --no-http`.

import os

CODE = os.environ["LW_PRODUCT_CODE"]
NAME = os.environ["LW_PRODUCT_NAME"]
COMPANY_NAME = os.environ["LW_COMPANY_NAME"]

company = env["res.company"].sudo().search([("name", "=", COMPANY_NAME)], limit=1)

Product = env["product.product"].sudo()
product = Product.search([("default_code", "=", CODE)], limit=1)

created = False
if not product:
    vals = {
        "name": NAME,
        "default_code": CODE,
        "type": "service",  # bundles are fulfilled offline; no inventory
        "sale_ok": True,
        "purchase_ok": False,
        "list_price": 0.0,
        "taxes_id": [(6, 0, [])],  # price is final (already charged in Stripe)
    }
    if company:
        vals["company_id"] = company.id
    product = Product.create(vals)
    created = True

env.cr.commit()

print(
    "OK"
    f" model=product.product code={CODE!r}"
    f" product_id={product.id}"
    f" created={created}"
    f" changed={created}"
)
