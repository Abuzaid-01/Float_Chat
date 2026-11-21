-- ============================================================================
-- FloatChat production migration: ocean_region column + float_id normalization
--
-- Applies to the LIVE Neon database (or local PostgreSQL). Idempotent — safe to
-- run more than once. Run against the `floatchat` database:
--
--   psql "$DATABASE_URL" -f add_ocean_region_and_normalize_float_id.sql
--   # or from Python: psycopg2/sqlalchemy execute the file contents
--
-- After running, the app code (models.py, data_loader.py, netcdf_extractor.py)
-- will classify regions and store clean float IDs automatically on new loads.
-- ============================================================================

BEGIN;

-- 1) Add the ocean_region column if it does not exist yet
ALTER TABLE public.argo_profiles ADD COLUMN IF NOT EXISTS ocean_region VARCHAR(50);

-- 2) Backfill ocean_region for existing rows from lat/lon
--    (same definitions as data_processing/regions.py and the SQL generator)
UPDATE public.argo_profiles
SET ocean_region = CASE
    WHEN latitude BETWEEN 12  AND 30  AND longitude BETWEEN 32  AND 44  THEN 'Red Sea'
    WHEN latitude BETWEEN 5  AND 20  AND longitude BETWEEN 92  AND 100 THEN 'Andaman Sea'
    WHEN latitude BETWEEN 5  AND 30  AND longitude BETWEEN 40  AND 80  THEN 'Arabian Sea'
    WHEN latitude BETWEEN 5  AND 25  AND longitude BETWEEN 80  AND 100 THEN 'Bay of Bengal'
    WHEN latitude BETWEEN -10 AND 5   AND longitude BETWEEN 40  AND 100 THEN 'Equatorial Indian Ocean'
    WHEN latitude BETWEEN -50 AND -10 AND longitude BETWEEN 20  AND 120 THEN 'Southern Indian Ocean'
    ELSE NULL
END
WHERE ocean_region IS NULL;

-- 3) Normalize float_id: strip the numpy byte-string wrapper "b'XXXXXX '"
UPDATE public.argo_profiles
SET float_id = regexp_replace(
                   regexp_replace(btrim(float_id), '^b[''"](.*)[''"]$', '\1'),
                   '''',
                   '',
                   'g'
               )
WHERE float_id IS NOT NULL;

UPDATE public.argo_profiles
SET float_id = btrim(float_id)
WHERE float_id IS NOT NULL;

-- 4) Index for region-filtered queries
CREATE INDEX IF NOT EXISTS idx_ocean_region ON public.argo_profiles (ocean_region);

-- 5) Re-analyze so the planner uses the new index + statistics
ANALYZE public.argo_profiles;

COMMIT;
