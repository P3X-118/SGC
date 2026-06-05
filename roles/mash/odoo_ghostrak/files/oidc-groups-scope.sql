-- Idempotently append :scope to auth_oauth_provider.scope for :client_id.
-- The WHERE clause skips rows that already contain the scope token (word-
-- boundary check via regex so `groupsx` doesn't false-positive on `groups`),
-- so psql reports `UPDATE 0` on no-op runs and the ansible task's
-- changed_when correctly reads idempotent.
--
-- Variables (provided via `psql -v key=value`):
--   :client_id — the auth_oauth_provider row to target
--   :scope     — the single OIDC scope to ensure is present
--
-- For a list of required scopes, the mash/odoo_ghostrak role's task loops
-- over odoo_ghostrak_oidc_required_scopes and runs this SQL once per scope.

UPDATE auth_oauth_provider
   SET scope = trim(
     CASE
       WHEN scope IS NULL OR scope = '' THEN :'scope'
       ELSE scope || ' ' || :'scope'
     END
   )
 WHERE client_id = :'client_id'
   AND (
        scope IS NULL
     OR scope = ''
     OR scope !~ ('(^|[[:space:]])' || :'scope' || '($|[[:space:]])')
   )
RETURNING client_id, scope;
