# Spatial Asset Manager

Web GIS platform to catalog, search, and preview tens of terabytes of orthophotos (GeoTIFF) and vector data (SHP, GeoJSON) stored on a Synology NAS using STAC-compliant metadata, FastAPI/PostGIS, and a React + Mapbox GL JS frontend.

## Goals
- Centralize metadata and lineage for raster and vector assets via STAC Collections/Items.
- Provide fast spatial/temporal search backed by PostgreSQL/PostGIS and expose REST/Tile endpoints.
- Enable map-based preview with multi-layer overlays, styling, and download links.
- Automate ingestion/validation jobs that read from the NAS mount and update the catalog.

## Tech Stack
- Backend: Python (FastAPI, Pydantic, SQLAlchemy/Alembic), STAC models/APIs, background workers for ingestion/tiling.
- Database: PostgreSQL + PostGIS for spatial indexing, search, and geometry operations.
- Frontend: React, Mapbox GL JS for interactive mapping, client-side querying, and previews.
- Data standards: STAC core spec (Collections, Items, Assets) for catalog interoperability.
- Tooling: Docker Compose for local orchestration; scripts for data ingestion, validation, and maintenance.

## Repository Structure
```
/                     # Project root
├─ backend/           # FastAPI service and supporting code
│  ├─ app/
│  │  ├─ api/         # Route definitions (REST/STAC API)
│  │  ├─ core/        # Settings, dependencies, security
│  │  ├─ db/          # Session management and migrations setup
│  │  ├─ models/      # ORM models (STAC, assets, users, jobs)
│  │  ├─ schemas/     # Pydantic schemas for requests/responses
│  │  ├─ services/    # Domain logic (catalog, search, auth)
│  │  ├─ stac/        # STAC-specific helpers, validators, converters
│  │  ├─ workers/     # Background jobs for ingestion/tiling/validation
│  │  └─ tests/       # Backend unit/integration tests
│  ├─ alembic/        # Migration scripts and env
│  ├─ pyproject.toml  # Backend dependencies and tooling config
│  └─ .env.example    # Backend environment variables (DB, NAS mount, tokens)
├─ frontend/          # React + Mapbox GL JS client
│  ├─ src/
│  │  ├─ components/  # UI components (map, layers, filters, tables)
│  │  ├─ pages/       # App pages (catalog, item detail, admin)
│  │  ├─ map/         # Map config, styles, sources, layer builders
│  │  ├─ services/    # API clients (STAC queries, auth)
│  │  ├─ hooks/       # Shared React hooks (data fetching, viewport state)
│  │  ├─ styles/      # Global styles/theme
│  │  └─ tests/       # Frontend tests
│  ├─ public/         # Static assets
│  ├─ package.json    # Frontend dependencies and scripts
│  └─ .env.example    # Frontend env (API base URL, Mapbox token)
├─ scripts/           # Operational scripts
│  ├─ ingest/         # Ingestion/ETL helpers to load NAS data into STAC catalog
│  ├─ maintenance/    # Validation, cleanup, backups, health checks
│  └─ dev/            # Local dev utilities (db reset, sample data)
├─ docker-compose.yml # Local orchestration (API, DB, worker, frontend)
└─ docs/              # Architecture decisions, API contracts, data standards
```

## Notes
- The NAS should be mounted read-only for ingestion jobs and surfaced via configured paths in the backend.
- STAC records drive both API responses and the frontend catalog; keep schema changes in sync across `backend/app/models`, `backend/app/schemas`, and `frontend/src/types` (when added).

## Quick Start (Docker + Sample Data)
This is a fast way to verify the ingestion flow and PostGIS storage.

### 1) Configure `.env`
Set the NAS path on the host (real path). The ingest container will always see the mounted data at `/data/nas`.
These paths are not the same; the host path is mapped into the container.

Examples of valid host paths:
- Synology DSM local path: `/volume1/data` or `/volume1/projects/gis`
- Linux host that mounts NAS via CIFS/NFS: `/mnt/nas/data` or `/data/nas`

How to decide the host path:
- If this project runs **on the NAS** (Docker on Synology), use the DSM path like `/volume1/<shared-folder>`.
- If this project runs **on another server**, use the mount point you configured (e.g., `/mnt/nas/...`).

Synology (Docker on NAS) example:
```
export NAS_DATA_ROOT=/volume1/data
docker compose --profile ingest run --rm ingest
```

External server (NAS mounted) example:
```
export NAS_DATA_ROOT=/mnt/nas/data
docker compose --profile ingest run --rm ingest
```
```
POSTGRES_USER=sam
POSTGRES_PASSWORD=sam_password
POSTGRES_DB=spatial_asset_manager
DB_PORT=5433
NAS_DATA_ROOT=/volume1/data
TZ=Asia/Seoul
```

### 2) Sample data (included)
This repo includes a small `sample-data` folder with a GeoJSON so you can test quickly.
It is safe to use for a first ingest run.

### 2) Start PostGIS
```
docker compose up -d
```

### 3) Build the ingest image
```
docker compose --profile ingest build
```

### 4) Run a sample ingest
For the sample run, temporarily override `NAS_DATA_ROOT` to point at the repo's `sample-data` folder.
```
NAS_DATA_ROOT=$(pwd)/sample-data docker compose --profile ingest run --rm ingest
```

For real NAS ingestion, just keep `NAS_DATA_ROOT` in `.env` (no override).

You can re-run the command to verify incremental updates (`items.nas_path` prevents duplicates).

### 5) Verify data with psql (optional)
```
docker exec spatial-asset-manager-db psql -U sam -d spatial_asset_manager \
  -c "SELECT COUNT(*) FROM items;" \
  -c "SELECT id, nas_path, assets->'data'->>'href' AS href FROM items LIMIT 5;"
```

## QGIS: PostGIS Connection
Use QGIS to visually confirm the indexed geometry.

1) `Layer` → `Data Source Manager` → `PostgreSQL` → `New`
2) Connection settings:
   - Host: `192.168.10.203` (or the host IP reachable from your QGIS machine)
   - Port: `5433`
   - Database: `spatial_asset_manager`
   - User: `sam`
   - Password: `sam_password`
3) `Test Connection` → `OK`
4) In the Browser panel, open the connection → `public` → `items` → add `geom` (EPSG:4326)
5) Right click the layer → `Zoom to Layer`

## TODO
- Define STAC-compliant API endpoints (Collections, Items, Search) with FastAPI.
- Implement ingestion job orchestration (queue/worker, retry, monitoring).
- Add asset preview pipeline (COG tiles, vector tiling, thumbnail generation).
- Build frontend catalog UI (map + table + filters) with React and Mapbox GL JS.
- Add auth/roles for admin vs. read-only access.
- Implement data validation and QC (schema checks, CRS checks, missing asset detection).
- Add observability (logging, metrics, job audit trails).
- Create backup/restore and data lifecycle policies.
