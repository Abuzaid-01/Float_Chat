-- ARGO Profiles Database Schema for Neon
-- This creates the complete database structure for ARGO float data

-- Set the schema to public
SET search_path TO public;

-- Drop table if exists (be careful!)
DROP TABLE IF EXISTS argo_profiles CASCADE;

-- Create main ARGO profiles table
CREATE TABLE public.argo_profiles (
    id SERIAL PRIMARY KEY,
    float_id VARCHAR(20),
    cycle_number INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timestamp TIMESTAMP,
    pressure DOUBLE PRECISION,
    temperature DOUBLE PRECISION,
    salinity DOUBLE PRECISION,
    
    -- BGC Parameters (currently NULL but available for future data)
    dissolved_oxygen DOUBLE PRECISION,
    chlorophyll DOUBLE PRECISION,
    ph DOUBLE PRECISION,
    nitrate DOUBLE PRECISION,
    
    -- Quality Control Flags
    temp_qc TEXT,
    sal_qc TEXT,
    
    -- Metadata
    platform_type TEXT,
    data_mode TEXT,
    ocean_region TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_float_id ON public.argo_profiles(float_id);
CREATE INDEX idx_cycle_number ON public.argo_profiles(cycle_number);
CREATE INDEX idx_timestamp ON public.argo_profiles(timestamp);
CREATE INDEX idx_location ON public.argo_profiles(latitude, longitude);
CREATE INDEX idx_ocean_region ON public.argo_profiles(ocean_region);
CREATE INDEX idx_temperature ON public.argo_profiles(temperature);
CREATE INDEX idx_salinity ON public.argo_profiles(salinity);
CREATE INDEX idx_pressure ON public.argo_profiles(pressure);

-- Create composite index for common queries
CREATE INDEX idx_float_cycle ON public.argo_profiles(float_id, cycle_number);
CREATE INDEX idx_location_time ON public.argo_profiles(latitude, longitude, timestamp);

-- Add comments to document the schema
COMMENT ON TABLE public.argo_profiles IS 'ARGO ocean float profile data with core and BGC parameters';
COMMENT ON COLUMN public.argo_profiles.float_id IS 'Unique identifier for ARGO float';
COMMENT ON COLUMN public.argo_profiles.cycle_number IS 'Dive cycle number';
COMMENT ON COLUMN public.argo_profiles.latitude IS 'Latitude in decimal degrees';
COMMENT ON COLUMN public.argo_profiles.longitude IS 'Longitude in decimal degrees';
COMMENT ON COLUMN public.argo_profiles.timestamp IS 'Measurement timestamp';
COMMENT ON COLUMN public.argo_profiles.pressure IS 'Pressure in decibar (depth proxy)';
COMMENT ON COLUMN public.argo_profiles.temperature IS 'Temperature in degrees Celsius';
COMMENT ON COLUMN public.argo_profiles.salinity IS 'Salinity in PSU (Practical Salinity Units)';
COMMENT ON COLUMN public.argo_profiles.dissolved_oxygen IS 'Dissolved oxygen in micromol/kg';
COMMENT ON COLUMN public.argo_profiles.chlorophyll IS 'Chlorophyll-a in mg/m³';
COMMENT ON COLUMN public.argo_profiles.ph IS 'pH on total scale';
COMMENT ON COLUMN public.argo_profiles.ocean_region IS 'Ocean region name';

-- Grant necessary permissions (Neon handles this automatically)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON argo_profiles TO neondb_owner;

ANALYZE public.argo_profiles;
