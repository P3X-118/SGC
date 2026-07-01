# Per-company document/email branding (idempotent). Run via `odoo-bin shell`.
# Env SGC_BRANDING_JSON = JSON list of
#   {name, primary, secondary, [email_primary], [email_secondary]}
# Sets res.company primary_color/secondary_color + email_primary_color/
# email_secondary_color. Prints "OK ..." + "changed=True|False".
import os
import json

C = env['res.company'].sudo()
changed = False
results = []

cfg = json.loads(os.environ.get('SGC_BRANDING_JSON') or '[]')
for entry in cfg:
    name = (entry.get('name') or '').strip()
    if not name:
        continue
    co = C.search([('name', '=', name)], limit=1)
    if not co:
        results.append(name + ':MISSING')
        continue
    primary = entry.get('primary')
    secondary = entry.get('secondary')
    email_primary = entry.get('email_primary') or primary
    email_secondary = entry.get('email_secondary') or secondary
    vals = {}
    if primary and co.primary_color != primary:
        vals['primary_color'] = primary
    if secondary and co.secondary_color != secondary:
        vals['secondary_color'] = secondary
    if email_primary and co.email_primary_color != email_primary:
        vals['email_primary_color'] = email_primary
    if email_secondary and co.email_secondary_color != email_secondary:
        vals['email_secondary_color'] = email_secondary
    if vals:
        co.write(vals)
        changed = True
        results.append('%s:set(%s)' % (name, ','.join(sorted(vals))))
    else:
        results.append(name + ':ok')

env.cr.commit()
print('OK branding %s changed=%s' % (results, changed))
