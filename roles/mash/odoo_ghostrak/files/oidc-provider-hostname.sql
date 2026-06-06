-- Re-point Odoo's auth_oauth_provider row for the ghostrak Authentik SSO at
-- the unified hostname so the browser shares its existing ghostrak session
-- cookie with Odoo (otherwise a user signed into ghostrak gets a second
-- Authentik login prompt when they hit Odoo — same Authentik backend, but
-- two distinct cookie domains).
--
-- Matched by client_id (the Authentik application slug Odoo holds in the
-- provider row). UPDATE is gated on `IS DISTINCT FROM` so re-runs that
-- already match are 0-row updates and changed_when=false.
--
-- The row itself was created ad-hoc (no ir_model_data xmlid) when the prime
-- engagement first set up SSO; we keep it in place (preserves the body
-- jsonb, the css_class, etc.) and only rewrite the endpoints.
UPDATE auth_oauth_provider
   SET auth_endpoint       = format('https://%s/application/o/authorize/', :'hostname'),
       validation_endpoint = format('https://%s/application/o/userinfo/',  :'hostname'),
       write_date          = NOW()
 WHERE client_id = :'client_id'
   AND (auth_endpoint       IS DISTINCT FROM format('https://%s/application/o/authorize/', :'hostname')
     OR validation_endpoint IS DISTINCT FROM format('https://%s/application/o/userinfo/',  :'hostname'));
