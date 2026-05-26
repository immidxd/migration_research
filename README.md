# BMS_React-PyWeb — Migrations Research

Desktop research tool for studying historical migration from Ukrainian lands
(XIX – early XX c.). Backend: FastAPI + PostgreSQL/PostGIS + SQLAlchemy.
Frontend: React + TypeScript + MapLibre GL + deck.gl. Wrapped as a desktop
app via pywebview.

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16 (local). The local EDB install lives at
  `/Library/PostgreSQL/16/`.
- **PostGIS extension** for that Postgres. Install via the EDB
  *Application Stack Builder*:
  *Spatial Extensions → PostGIS 3.x for PostgreSQL 16*.
  Until PostGIS is installed, `alembic upgrade head` will fail at the
  `CREATE EXTENSION postgis` step — by design.

## Database

The project uses a dedicated database `migrationsdb` on the local Postgres
instance. Existing databases (`bsstorage`, `financedb`) are not touched.

```bash
/Library/PostgreSQL/16/bin/createdb -U postgres migrationsdb
```

## Setup

```bash
cp .env.example .env       # edit credentials if needed
./run.sh migrate           # run Alembic migrations (needs PostGIS)
./run.sh                   # launch the desktop app
```

`./run.sh build` builds the production frontend bundle that the backend
serves; `./run.sh` then opens it in a pywebview window.

## Layout

```
backend/   FastAPI app, SQLAlchemy models, Alembic migrations, services
frontend/  React + TS + Tailwind + MapLibre/deck.gl
desktop/   pywebview wrappers (entrypoint is project-root main.py)
data/      historical-territory shapefiles, basemaps, fixtures
secrets/   Google service account JSON (gitignored)
```

## Academic rules baked into the schema

- Every fact carries an explicit `precision_level` (point → region).
- Records of vague origin (e.g. "Pravoberezhzhia") are bound to the
  umbrella region's polygon and **never** redistributed across child
  gubernias by the application.
- Every fact must cite a `source`.
