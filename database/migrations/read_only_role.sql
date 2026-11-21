-- Run once with maintenance credentials on the database that hosts FloatChat.
-- Set the login password through your database provider, then use that role in
-- the API's DATABASE_URL. Keep the maintenance role for imports and migrations.

CREATE ROLE floatchat_api LOGIN;

GRANT USAGE ON SCHEMA public TO floatchat_api;
GRANT SELECT ON public.argo_profiles TO floatchat_api;

ALTER ROLE floatchat_api SET default_transaction_read_only = on;
ALTER ROLE floatchat_api SET statement_timeout = '12s';
