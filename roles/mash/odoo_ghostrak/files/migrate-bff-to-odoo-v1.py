# SGC: one-shot migration of pre-seam-#7 BFF Postgres state into Odoo
# res.partner records (seam #7 phase 4a). After this runs, Odoo is the
# canonical source of truth for facilities + players + assignments; the
# BFF tables (facility, facility_role, player, player_coach) become
# obsolete and are dropped in a later phase.
#
# Snapshot of the BFF state we're migrating (prod, captured 2026-06-06):
#   Facilities (2):
#     a1d9fb98-...-d1a87fc  Prime Baseball   -> matches existing res.partner id=1
#     6676e5c3-...-997534   MKCHS            -> needs creation
#   Player (1):
#     836b48a6-...-cac427f11  little billy pancakes
#       facility = Prime Baseball
#       peertube_channel = grp836b48a6c1c548c2
#       peertube_channel_id = 14
#       linked_user_email = NULL  (no Authentik identity to attach yet)
#   facility_role: 0 rows
#   player_coach:  0 rows
#   session:       0 rows
#
# Dev (go.ghostrak.app) is empty — running this script there is harmless
# (every find-or-create resolves "already present" or creates the records
# fresh; both end states are correct).
#
# Idempotency: marker key `ghostrak.migration.bff_to_odoo_v1` in
# ir.config_parameter. Once set to 'done', the script exits early.
# Without the marker, find-or-create handles re-runs too — the marker
# is the fast-path exit, not the only safety.

import logging

MARKER_KEY = "ghostrak.migration.bff_to_odoo_v1"
MARKER_VALUE = "done"

FACILITIES = [
    {"name": "Prime Baseball", "bff_uuid": "a1d9fb98-5593-47c9-a002-e7c41d1a87fc"},
    {"name": "MKCHS",          "bff_uuid": "6676e5c3-29ee-441b-8659-1b2607997534"},
]

PLAYERS = [
    {
        "name": "little billy pancakes",
        "bff_uuid": "836b48a6-c1c5-48c2-b940-d64cac427f11",
        "facility_name": "Prime Baseball",
        "peertube_channel": "grp836b48a6c1c548c2",
        "peertube_channel_id": 14,
        "linked_user_email": None,
    },
]

Partner = env["res.partner"].sudo()
ICP = env["ir.config_parameter"].sudo()

# Multi-tenant isolation: every ghostrak-roled partner must have a company_id
# (enforced by the addon's _check_ghostrak_company_required constraint). On
# this single-company prime deploy that's the main Odoo company; if the
# deploy later splits each facility into its own Odoo company, this script
# becomes a per-company loop instead of a single shared default.
DEFAULT_COMPANY_ID = env.company.id

existing_marker = ICP.get_param(MARKER_KEY) or ""
if existing_marker == MARKER_VALUE:
    print(f"OK changed=False migrated=already_done marker={MARKER_KEY}")
else:
    facilities_attached = 0
    facilities_created = 0
    players_attached = 0
    players_created = 0
    skipped_role_conflict = 0

    facility_partner_by_name = {}

    # ---- Facilities -------------------------------------------------------
    # Lookup order:
    #  1. ghostrak_facility_uuid match (canonical — set by this script after
    #     attach/create so re-runs are deterministic).
    #  2. exact name match (covers Prime Baseball, which already exists as the
    #     Odoo company itself at id=1).
    #  3. create new partner.
    for f in FACILITIES:
        name = f["name"]
        bff_uuid = f["bff_uuid"]
        existing = Partner.search([("ghostrak_facility_uuid", "=", bff_uuid)], limit=1)
        if not existing:
            existing = Partner.search([("name", "=", name)], limit=1)
        if existing:
            if existing.ghostrak_role and existing.ghostrak_role != "none" and \
                    existing.ghostrak_role != "facility":
                # Existing partner with a non-facility role — refuse to
                # silently coerce it. Log and skip; an operator handles it.
                print(f"WARN skipping facility name={name} id={existing.id} "
                      f"existing_role={existing.ghostrak_role}")
                skipped_role_conflict += 1
                continue
            updates = {}
            if existing.ghostrak_role != "facility":
                updates["ghostrak_role"] = "facility"
            if existing.ghostrak_facility_uuid != bff_uuid:
                updates["ghostrak_facility_uuid"] = bff_uuid
            if not existing.company_id:
                updates["company_id"] = DEFAULT_COMPANY_ID
            if updates:
                existing.write(updates)
                facilities_attached += 1
            facility_partner_by_name[name] = existing
        else:
            created = Partner.create({
                "name": name,
                "is_company": True,
                "ghostrak_role": "facility",
                "ghostrak_facility_uuid": bff_uuid,
                "company_id": DEFAULT_COMPANY_ID,
            })
            facility_partner_by_name[name] = created
            facilities_created += 1

    # ---- Players ----------------------------------------------------------
    for p in PLAYERS:
        name = p["name"]
        facility_partner = facility_partner_by_name.get(p["facility_name"])
        if not facility_partner:
            print(f"WARN skipping player name={name} — facility "
                  f"{p['facility_name']} did not resolve")
            continue

        existing = Partner.search([("name", "=", name)], limit=1)
        if existing:
            if existing.ghostrak_role and existing.ghostrak_role != "none" and \
                    existing.ghostrak_role != "player":
                print(f"WARN skipping player name={name} id={existing.id} "
                      f"existing_role={existing.ghostrak_role}")
                skipped_role_conflict += 1
                continue
            existing.write({
                "ghostrak_role": "player",
                "ghostrak_facility_id": facility_partner.id,
                "ghostrak_peertube_channel": p["peertube_channel"],
                "ghostrak_peertube_channel_id": p["peertube_channel_id"],
                "ghostrak_authentik_email": p["linked_user_email"] or False,
                # Players live in their facility's company so the tenant rule
                # ranges through evenly. facility_partner.company_id is set
                # above (or pre-existed); fall through to the default if not.
                "company_id": facility_partner.company_id.id or DEFAULT_COMPANY_ID,
            })
            players_attached += 1
        else:
            Partner.create({
                "name": name,
                "ghostrak_role": "player",
                "ghostrak_facility_id": facility_partner.id,
                "ghostrak_peertube_channel": p["peertube_channel"],
                "ghostrak_peertube_channel_id": p["peertube_channel_id"],
                "ghostrak_authentik_email": p["linked_user_email"] or False,
                "company_id": facility_partner.company_id.id or DEFAULT_COMPANY_ID,
            })
            players_created += 1

    # ---- Marker -----------------------------------------------------------
    # Only stamp the marker if NO role conflicts blocked work. A conflict
    # leaves the script re-runnable so an operator can resolve and retry.
    if skipped_role_conflict == 0:
        ICP.set_param(MARKER_KEY, MARKER_VALUE)

    env.cr.commit()

    changed = (facilities_attached or facilities_created or
               players_attached or players_created) > 0
    print(
        "OK"
        f" changed={changed}"
        f" facilities_attached={facilities_attached}"
        f" facilities_created={facilities_created}"
        f" players_attached={players_attached}"
        f" players_created={players_created}"
        f" skipped_role_conflict={skipped_role_conflict}"
        f" marker_set={skipped_role_conflict == 0}"
    )
