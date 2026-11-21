# FloatChat

FloatChat is a conversational explorer for the Argo ocean-float archive. The **Ocean Observatory** is the Next.js frontend in `nexus-saa-s-ai-platform`. The primary backend is `api.main:app`, a FastAPI application that reads measurements from PostgreSQL.

## How answers are produced

1. FastAPI classifies the question and passes the recent user turns to the query processor.
2. The deterministic parser resolves supported questions about dates, regions, floats, pressure, and core measurements. It generates SQL from the resolved filters. Relative dates are anchored to the newest observation in the loaded archive.
3. For free-form questions, MiniLM, FAISS, and BM25 retrieve relevant profile summaries. Reciprocal rank fusion combines the two search rankings. The summaries, archive dates, schema, and curated SQL examples guide GPT-OSS 120B on Groq in writing a PostgreSQL query.
4. The backend executes the query and builds the reply from the returned values. The UI shows the SQL, result rows, charts when applicable, and the retrieved summaries for model-written SQL.

The RAG index contains **profile summaries**. PostgreSQL stores individual pressure-level **measurements**. Float counts use distinct float IDs, and profile counts use distinct float/cycle pairs with both identifiers present. The bundled SQL dump and daily CSVs are separate snapshots. The API reports coverage for its connected database.

Thermocline and water-mass requests select a single timestamped cast and run Python analysis on its usable pressure levels. These algorithms are estimates. Water-mass labels reflect reference temperature, salinity, and pressure ranges.

Only exact free-form requests with the same context reuse generated SQL. Each request reads fresh database rows. An empty result keeps the original scope.

## Local development

Use Python 3.11 or 3.12, PostgreSQL with the Argo schema, and Node.js with pnpm. In a fresh checkout:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
pnpm --dir nexus-saa-s-ai-platform install
```

Set `DATABASE_URL` in `.env`. The database must contain `public.argo_profiles`, with canonical `ocean_region` and normalized float IDs. For an older archive, see [the archive normalization migration](database/migrations/add_ocean_region_and_normalize_float_id.sql). Use a separate [read-only database role](database/migrations/read_only_role.sql) for the web API.

Set `GROQ_API_KEY` for free-form RAG and leave `GROQ_MODEL=openai/gpt-oss-120b` to use the project default. Supported structured questions run without Groq. Set `VECTOR_STORE_PATH` to the directory containing `index.faiss` and `metadata.pkl`. The repository includes an initial index. Build or refresh your profile index from the same archive when changing datasets, using `scripts/generate_summaries.py` and `scripts/populate_vector_db.py` with your maintenance credentials.

Run `./start.sh` and open [the Ocean Observatory](http://127.0.0.1:3000). Swagger is available at [the local API docs](http://127.0.0.1:8000/docs).

### Try these queries

| Query | Expected behavior |
|---|---|
| How many floats are there? | Counts distinct float IDs. |
| How many measurements are in the Arabian Sea at pressures below 100 dbar? | Applies an exact pressure and region filter. |
| Show average temperature in the Arabian Sea on October 12 2025. | Uses an explicit date and temperature QC. |
| What about salinity? | Retains the region and date from the previous supported question. |
| Calculate thermocline depth for float 2903956. | Selects a usable cast and returns pressure samples plus thermocline estimates. |
| What is the variance of surface temperature in the Arabian Sea? | Uses the free-form RAG route and returns its retrieved profile summaries. |

## Tests and deployment

```bash
.venv/bin/python -m pip install pytest httpx
.venv/bin/python -m pytest -q
pnpm --dir nexus-saa-s-ai-platform build
```

The API integration tests exercise the real query processor with a disposable SQL fixture. Tests stub external model inference. A release smoke test should also exercise the target PostgreSQL archive and submit a free-form question with the deployed Groq configuration.

On Netlify, `netlify.toml` sets `NEXT_PUBLIC_API_MODE=netlify`. Set the existing Neon's
read-only connection URL as the server-side `DATABASE_URL` in Netlify's Functions
environment. The frontend calls its own `/api/v1/` routes for archive health,
dashboard stats, region and float lookups, and chat with maps, profiles, and
daily trends. Set the server-side `GROQ_API_KEY` in Netlify Functions to enable
optional model-assisted interpretation for supported archive analyses. The
model returns a validated plan; the API builds parameterized read-only SQL.
Test
`/api/v1/health?deep=true` after deployment. Optionally keep the existing HTTPS
`NEXT_PUBLIC_API_BASE_URL` or set `FLOATCHAT_LEGACY_API_URL` server-side for chat
questions that need the Python pipeline.

For a separate FastAPI deployment, serve `api.main:app`, leave
`NEXT_PUBLIC_API_MODE` unset, and set `NEXT_PUBLIC_API_BASE_URL` to the API's public
URL at frontend build time. Set `CORS_ORIGINS` to the frontend origins.
Free-form queries require a readable profile index and working provider credentials.

## Project history

The Streamlit dashboard, the older landing-page components, and the MCP-style Python tool code remain available for reference. The primary Next.js and FastAPI path calls the query and analytics functions directly. The older deployment and architecture guides describe the Streamlit-era prototype.
