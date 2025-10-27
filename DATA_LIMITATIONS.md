# 📊 FloatChat Data Limitations & BGC Parameters

**Last Updated:** October 27, 2025  
**Database Records:** 1,268,992 ARGO profiles

---

## 🌊 Current Data Status

### ✅ Available Data (Core ARGO)

Your database currently contains **Core ARGO measurements** from standard ARGO floats:

| Parameter | Status | Records | Description |
|-----------|--------|---------|-------------|
| **Temperature** | ✅ Available | 1,268,992 | Sea water temperature (°C) |
| **Salinity** | ✅ Available | 1,268,992 | Practical Salinity Units (PSU) |
| **Pressure** | ✅ Available | 1,268,992 | Water pressure in decibars (dbar ≈ depth in meters) |
| **Latitude/Longitude** | ✅ Available | 1,268,992 | Geographic coordinates |
| **Timestamp** | ✅ Available | 1,268,992 | Measurement date and time |

### ❌ Unavailable Data (BGC ARGO)

The following **biogeochemical (BGC) parameters** are **NOT currently available**:

| Parameter | Status | Records | Reason |
|-----------|--------|---------|--------|
| **pH** | ❌ Not Available | 0 | Data source contains Core ARGO only |
| **Dissolved Oxygen** | ❌ Not Available | 0 | Data source contains Core ARGO only |
| **Chlorophyll** | ❌ Not Available | 0 | Data source contains Core ARGO only |
| **Nitrate** | ❌ Not Available | 0 | Not included in current schema |
| **BBP700** | ❌ Not Available | 0 | Not included in current schema |

---

## 🔬 Understanding ARGO vs BGC-ARGO

### Core ARGO Floats (~90% of fleet)
- **Measure:** Temperature, Salinity, Pressure
- **Purpose:** Physical oceanography
- **Data Files:** Usually named `*_prof.nc` or `*R_prof.nc`
- **Your Current Data:** ✅ This is what you have

### BGC-ARGO Floats (~10% of fleet)
- **Measure:** All Core parameters PLUS biogeochemical parameters
- **Purpose:** Biogeochemical oceanography
- **Data Files:** Usually named `*B_prof.nc` or `*BR_prof.nc` (note the 'B')
- **Your Current Data:** ❌ You don't have this yet

---

## 🚫 Queries That Won't Work (Currently)

The following types of queries will **fail or return empty results**:

### pH-related Queries
```
❌ "Show pH trends in Indian Ocean over time"
❌ "What is the average pH in Arabian Sea?"
❌ "Find areas with low pH levels"
❌ "Ocean acidification analysis"
```

### Dissolved Oxygen Queries
```
❌ "Show dissolved oxygen levels in Bay of Bengal"
❌ "Find oxygen minimum zones"
❌ "Analyze hypoxic conditions"
```

### Chlorophyll Queries
```
❌ "Show chlorophyll distribution"
❌ "Find high productivity zones"
❌ "Analyze phytoplankton patterns"
```

### BGC Temporal Trends
```
❌ "Analyze oxygen trends over time"
❌ "Show seasonal pH variations"
❌ "Track biogeochemical changes"
```

---

## ✅ Queries That WILL Work

You can perform comprehensive analysis with Core ARGO parameters:

### Temperature Analysis
```
✅ "Show temperature profiles in Arabian Sea"
✅ "Find temperature anomalies"
✅ "Analyze thermocline depth"
✅ "Temperature trends over time"
✅ "Identify warm/cold water masses"
```

### Salinity Analysis
```
✅ "Show salinity distribution in Indian Ocean"
✅ "Find high salinity regions"
✅ "Analyze halocline characteristics"
✅ "Salinity trends over time"
```

### Water Mass Identification
```
✅ "Identify water masses based on T-S characteristics"
✅ "Compare water properties between regions"
✅ "Find similar oceanographic profiles"
```

### Mixed Layer Depth
```
✅ "Calculate mixed layer depth"
✅ "Analyze surface layer characteristics"
✅ "Find deep mixing events"
```

### Geographic Analysis
```
✅ "Show float distribution"
✅ "Find nearest floats to a location"
✅ "Analyze spatial coverage"
✅ "Regional comparisons"
```

### Temporal Analysis
```
✅ "Analyze temperature trends over time"
✅ "Show seasonal variations"
✅ "Find recent measurements"
```

---

## 📥 How to Add BGC Data

If you need BGC parameters, you have several options:

### Option 1: Download BGC-ARGO Data

1. **Visit ARGO Data Centers:**
   - IFREMER: https://www.seanoe.org/data/00311/42182/
   - GDAC: https://www.ocean-ops.org/board

2. **Look for BGC files:**
   - Files with 'B' in the name: `*B_prof.nc` or `*BR_prof.nc`
   - Synthetic files: `*S_prof.nc` (combined BGC parameters)

3. **Filter by Parameters:**
   - Check for: DOXY (dissolved oxygen), CHLA (chlorophyll), PH_IN_SITU_TOTAL

### Option 2: Load BGC Data from Your NetCDF Files

If your NetCDF files contain BGC parameters:

```python
# Update data_processing/netcdf_importer.py to extract BGC parameters
from netCDF4 import Dataset

def load_bgc_data(netcdf_file):
    with Dataset(netcdf_file, 'r') as nc:
        # Check for BGC parameters
        if 'PH_IN_SITU_TOTAL' in nc.variables:
            ph = nc.variables['PH_IN_SITU_TOTAL'][:]
            # Process and insert into database
```

### Option 3: Load Pre-processed BGC Data

If you have BGC data in CSV format:

```python
import pandas as pd

# Load BGC CSV
bgc_df = pd.read_csv('bgc_data.csv')

# Insert into database
# Ensure columns match: ph, dissolved_oxygen, chlorophyll
```

---

## 🛠️ Database Schema

Your database **already has BGC columns** - they just need data!

```sql
-- Current schema (columns exist, data is NULL)
CREATE TABLE argo_profiles (
    -- Core ARGO (populated ✅)
    id SERIAL PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timestamp TIMESTAMP,
    temperature DOUBLE PRECISION,
    salinity DOUBLE PRECISION,
    pressure DOUBLE PRECISION,
    
    -- BGC ARGO (columns exist, but all NULL ❌)
    dissolved_oxygen DOUBLE PRECISION,  -- Currently all NULL
    chlorophyll DOUBLE PRECISION,       -- Currently all NULL
    ph DOUBLE PRECISION,                -- Currently all NULL
    
    -- QC and metadata
    temp_qc INTEGER,
    sal_qc INTEGER,
    data_mode VARCHAR(1),
    platform_type VARCHAR(50)
);
```

To populate BGC data, you just need to:
1. Load BGC-ARGO NetCDF files
2. Update the import script to extract BGC parameters
3. Insert data into existing columns

---

## 📈 Impact on MCP Tools

### Tools That Work Normally ✅
- `query_argo_data` - Full functionality with Core parameters
- `get_database_schema` - Works perfectly
- `search_similar_profiles` - Works with T-S profiles
- `analyze_float_profile` - Works with Core data
- `calculate_thermocline` - Works with temperature profiles
- `identify_water_masses` - Works with T-S characteristics
- `compare_regions` - Works with Core parameters
- `analyze_temporal_trends` - Works with temperature/salinity
- `calculate_mixed_layer_depth` - Works with Core data

### Tools With Limited Functionality ⚠️
- `get_bgc_parameters` - **Will return empty results**
  - Returns error message explaining BGC data is unavailable
  - Suggests loading BGC-ARGO data

---

## 🎯 Recommendations

### For Current Analysis (Without BGC)
Focus on physical oceanography:
- Temperature and salinity distributions
- Water mass identification
- Mixed layer dynamics
- Thermocline/halocline analysis
- Regional comparisons
- Temporal trends in T-S

### To Enable BGC Analysis
1. **Identify data needs:**
   - Which BGC parameters do you need? (pH, DO, Chlorophyll)
   - Which ocean regions?
   - What time period?

2. **Download BGC data:**
   - Visit ARGO GDAC
   - Filter for BGC floats ('B' files)
   - Focus on Indian Ocean region

3. **Update import scripts:**
   - Modify `netcdf_importer.py` to extract BGC variables
   - Add BGC parameter mapping

4. **Reload database:**
   - Import BGC NetCDF files
   - Verify data population

---

## 🔍 Quick Data Check

To verify what data you have, run:

```python
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from sqlalchemy import func

db_setup = DatabaseSetup()
session = db_setup.get_session()

# Check Core ARGO
temp_count = session.query(func.count(ArgoProfile.id)).filter(
    ArgoProfile.temperature.isnot(None)
).scalar()
print(f"Temperature records: {temp_count:,}")

# Check BGC ARGO  
ph_count = session.query(func.count(ArgoProfile.id)).filter(
    ArgoProfile.ph.isnot(None)
).scalar()
print(f"pH records: {ph_count:,}")

session.close()
```

**Expected Output (Current):**
```
Temperature records: 1,268,992
pH records: 0
```

---

## 📞 Support

If you need help:
1. Loading BGC data
2. Modifying import scripts
3. Understanding ARGO data structure
4. Accessing specific BGC parameters

Contact the FloatChat development team or consult ARGO documentation at https://argo.ucsd.edu/

---

**Note:** This limitation is **data-dependent**, not a software limitation. The FloatChat system is fully capable of handling BGC parameters once the data is loaded into the database.
