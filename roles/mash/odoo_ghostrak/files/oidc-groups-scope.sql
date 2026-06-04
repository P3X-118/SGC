-- Idempotently append `groups` to auth_oauth_provider.scope for the named
-- client. The WHERE clause skips rows that already include the token
-- `groups` (word-boundary check via regex so `groupsx` doesn't false-
-- positive), so psql reports `UPDATE 0` on subsequent runs and the ansible
-- task's changed_when correctly reads no-op.
--
-- :client_id is provided via `psql -v client_id=<value>` (set by the
-- mash/odoo_ghostrak role's task).

UPDATE auth_oauth_provider
   SET scope = trim(
     CASE
       WHEN scope IS NULL OR scope = '' THEN 'groups'
       ELSE scope || ' groups'
     END
   )
 WHERE client_id = :'client_id'
   AND (
        scope IS NULL
     OR scope = ''
     OR scope !~ '(^|[[:space:]])groups($|[[:space:]])'
   )
RETURNING client_id, scope;
