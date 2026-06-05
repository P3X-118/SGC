-- Idempotently UPSERT a single ir_config_parameter row. Returns the row only
-- when something actually changed (insert or update-where-different), so the
-- ansible task's changed_when reads `INSERT 0 1` for real changes and
-- `INSERT 0 0` for no-ops.
--
-- Variables (provided via `psql -v key=value`):
--   :param_key   — the ir_config_parameter.key string
--   :param_value — the value to write
--
-- The ON CONFLICT clause's WHERE prevents a touch-update when the value is
-- already correct — Odoo's write_date column would otherwise be bumped on
-- every run and look like a real change in audit logs.

INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
VALUES (:'param_key', :'param_value', 1, NOW(), 1, NOW())
ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value,
        write_uid = 1,
        write_date = NOW()
    WHERE ir_config_parameter.value IS DISTINCT FROM EXCLUDED.value
RETURNING key;
