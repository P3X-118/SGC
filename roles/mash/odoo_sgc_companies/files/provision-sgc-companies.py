# Ensure the SGC multi-company setup (idempotent). Run via `odoo-bin shell`.
#
# Model: SGC is the OPERATOR / home company (company id 1). The other companies
# are INDEPENDENT legal entities that SGC's staff MANAGE via multi-company access
# — they are NOT branches/subsidiaries of SGC, so they carry NO parent_id
# (no consolidation hierarchy). Every company is top-level; SGC's internal users
# get access to all of them + the Multi-Companies group (the company switcher).
#
# Env:
#   SGC_OPERATOR - display name for the home company (id 1), e.g. "SGC"
#   SGC_MANAGED  - comma-separated managed company names
# Prints "OK ..." + "changed=True|False" (the role's failed_when/changed_when keys).
import os
from odoo import SUPERUSER_ID

C = env['res.company'].sudo()
U = env['res.users'].sudo()
changed = False

operator_name = (os.environ.get('SGC_OPERATOR') or 'SGC').strip()
managed = [c.strip() for c in (os.environ.get('SGC_MANAGED') or '').split(',') if c.strip()]

# Company 1 is the operator / home company.
operator = C.browse(1)
if operator.name != operator_name:
    operator.name = operator_name
    changed = True

# Create declared managed companies (get-or-create by name) as TOP-LEVEL
# companies — no parent_id, because they are independent, not branches of SGC.
for name in managed:
    if not C.search([('name', '=', name)], limit=1):
        C.create({'name': name})
        changed = True

# Independent, not branches: keep every company flat. Odoo forbids changing
# parent_id through the ORM ("The company hierarchy cannot be changed."), so
# self-heal any company left parented by an earlier model directly in SQL — and
# fix the stored parent_path (res.company is a parent_store model: a top-level
# company's path is just "<id>/"). Safe here: these are fresh companies with no
# transactional data. Idempotent (no-op once everything is already flat).
env.cr.execute("UPDATE res_company SET parent_id = NULL WHERE parent_id IS NOT NULL")
if env.cr.rowcount:
    changed = True
env.cr.execute(
    "UPDATE res_company SET parent_path = id::text || '/' "
    "WHERE parent_path IS DISTINCT FROM (id::text || '/')"
)
env.registry.clear_cache()

# Access model — company isolation. ONLY SGC Super Admins may reach companies
# other than their own. "Super Admin" == Odoo base.group_system, which the
# sgc_login addon keeps in sync with the Authentik SGC-super-admin group on every
# SSO login (Authentik is the source of truth). Super Admins get ALL companies +
# the Multi-Companies group (company switcher; they manage other companies/users).
# Every other internal user is CONFINED to their own company. Super Admins also
# get FULL functional access by mirroring the reference admin (base.user_admin),
# which Odoo auto-subscribes to every app's groups on install — so they can see/use
# every installed app, not just Settings. OdooBot + base.user_admin are always
# treated as Super Admins (break-glass).
admin_grp = env.ref('base.group_system')
mc = env.ref('base.group_multi_company', raise_if_not_found=False)
all_companies = C.search([])
ref_admin = env.ref('base.user_admin')
break_glass = {SUPERUSER_ID, ref_admin.id}

for u in U.search([('share', '=', False), ('active', '=', True)]):
    is_super = (u.id in break_glass) or (admin_grp in u.group_ids)
    if is_super:
        missing = all_companies - u.company_ids
        if missing:
            u.company_ids = [(4, c.id) for c in missing]
            changed = True
        if mc and mc not in u.group_ids:
            u.group_ids = [(4, mc.id)]
            changed = True
        # Full app access: mirror base.user_admin's groups (idempotent superset).
        if u.id != ref_admin.id:
            extra = ref_admin.group_ids - u.group_ids
            if extra:
                u.group_ids = [(4, g.id) for g in extra]
                changed = True
    else:
        # Confine to their own company only (never leave them with extra access).
        own = u.company_id or u.company_ids[:1]
        if own and set(u.company_ids.ids) != set(own.ids):
            u.company_ids = [(6, 0, own.ids)]
            changed = True
        if mc and mc in u.group_ids:
            u.group_ids = [(3, mc.id)]
            changed = True

# Chart of accounts per company — so each managed company can ACTUALLY invoice.
# The companies were created with chart_template set, but the generic CoA was
# only ever loaded for the operator (company 1); load it for any company still
# missing its own receivable account. Idempotent and safe here (these companies
# have no journal entries). Without this, a company-confined user cannot create a
# customer / order / invoice — Odoo raises "no company crossover allowed" because
# the partner's A/R + A/P default to the operator's accounts.
CT = env['account.chart.template'].sudo()
A = env['account.account'].sudo()
coa_loaded = []
coa_failed = []
for comp in all_companies:
    has_recv = A.search_count([('account_type', '=', 'asset_receivable'),
                               ('company_ids', 'in', comp.id)])
    if not has_recv:
        # Fail-SOFT per company: a CoA template collision (seen live: loading a
        # new company's CoA tripped "no company crossover" against 30A's Bank
        # journal) must not roll back company creation / confinement for
        # everyone. Companies that only hold contacts (e.g. the eagledrive
        # dossier mirror) don't need accounting; load CoA for the ones that
        # can, WARN loudly for the ones that can't.
        try:
            with env.cr.savepoint():
                CT.try_loading('generic_coa', company=comp, install_demo=False)
            coa_loaded.append(comp.name)
            changed = True
        except Exception as e:  # noqa: BLE001 — surfaced in the play output
            coa_failed.append(f"{comp.name}: {e}")
if coa_loaded:
    env.cr.commit()
if coa_failed:
    print("WARN coa_load_failed=" + "; ".join(coa_failed))

env.cr.commit()
companies = sorted(C.search([]).mapped('name'))
supers = sorted(U.search([('share', '=', False), ('active', '=', True)]).filtered(
    lambda x: x.id in break_glass or admin_grp in x.group_ids).mapped('login'))
print("OK operator=%s managed=%s all=%s superadmins=%s coa_loaded=%s changed=%s" % (
    operator_name, managed, companies, supers, coa_loaded, changed))
