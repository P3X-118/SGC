# SGC: provision The Learning Well as a managed Odoo company (multi-company;
# 30A is company 1). Idempotent — keyed on the company name, so re-runs and a
# fresh/migrated Odoo converge to the same single company. Run via
# `odoo-bin shell --no-http` in a one-shot docker run (same image/mounts/network
# as the long-running do service; no downtime).

import os

NAME = os.environ["LW_COMPANY_NAME"]
CURRENCY = os.environ.get("LW_COMPANY_CURRENCY", "USD")
COUNTRY = os.environ.get("LW_COMPANY_COUNTRY", "US")

Company = env["res.company"].sudo()
company = Company.search([("name", "=", NAME)], limit=1)

created = False
if not company:
    vals = {"name": NAME}

    currency = (
        env["res.currency"].sudo().with_context(active_test=False).search([("name", "=", CURRENCY)], limit=1)
    )
    if currency:
        if not currency.active:
            currency.active = True  # a company's currency must be active
        vals["currency_id"] = currency.id

    country = env["res.country"].sudo().search([("code", "=", COUNTRY)], limit=1)
    if country:
        vals["country_id"] = country.id

    company = Company.create(vals)  # also creates the linked res.partner
    created = True

env.cr.commit()

print(
    "OK"
    f" model=res.company name={NAME!r}"
    f" company_id={company.id}"
    f" created={created}"
    f" changed={created}"
)
