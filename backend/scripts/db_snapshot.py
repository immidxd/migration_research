"""Portable database snapshot — dump/restore the WHOLE database to a file
inside the project, so the project folder is self-contained and movable.

Why this exists: reference geodata can be rebuilt anywhere with the seeders,
but the user's *facts* (migration_flows, territory_stats, sources, periods…)
live only in Postgres. This snapshots everything — schema + data — into
data/fixtures/ so copying the project folder carries the full working state.

Usage (via run.sh):
    ./run.sh backup     # dump current DB  -> data/fixtures/migrationsdb.dump
    ./run.sh restore    # restore that dump into the configured DB

Or directly:
    python -m backend.scripts.db_snapshot dump
    python -m backend.scripts.db_snapshot restore

Uses Postgres' custom format (pg_dump -Fc) — compact and restorable with
pg_restore. Finds pg_dump/pg_restore on PATH or in common install locations.
Connection comes from DATABASE_URL (the same one the app uses).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from backend.app.settings import PROJECT_ROOT, get_settings


DUMP_PATH = PROJECT_ROOT / "data" / "fixtures" / "migrationsdb.dump"

# Common macOS / Linux locations to look for the Postgres client binaries
# if they're not already on PATH.
_BIN_HINTS = [
    "/Library/PostgreSQL/16/bin",
    "/Library/PostgreSQL/15/bin",
    "/opt/homebrew/opt/postgresql@16/bin",
    "/usr/local/opt/postgresql@16/bin",
    "/usr/lib/postgresql/16/bin",
]


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for hint in _BIN_HINTS:
        cand = Path(hint) / name
        if cand.exists():
            return str(cand)
    raise FileNotFoundError(
        f"{name} not found on PATH or in {_BIN_HINTS}. Install the Postgres "
        "client tools or add their bin/ to PATH."
    )


def _conn_env() -> tuple[dict[str, str], str]:
    """Parse DATABASE_URL into libpq PG* env vars + the database name."""
    url = get_settings().database_url
    # strip SQLAlchemy driver suffix, e.g. postgresql+psycopg2 -> postgresql
    scheme_clean = url.split("+", 1)[0] + "://" + url.split("://", 1)[1]
    p = urlparse(scheme_clean)
    env = dict(os.environ)
    if p.hostname:
        env["PGHOST"] = p.hostname
    if p.port:
        env["PGPORT"] = str(p.port)
    if p.username:
        env["PGUSER"] = unquote(p.username)
    if p.password:
        env["PGPASSWORD"] = unquote(p.password)
    dbname = (p.path or "/").lstrip("/")
    return env, dbname


def dump() -> None:
    env, dbname = _conn_env()
    DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _tool("pg_dump"), "-Fc", "--no-owner", "--no-privileges",
        "-d", dbname, "-f", str(DUMP_PATH),
    ]
    print(f"Dumping {dbname} -> {DUMP_PATH}")
    subprocess.run(cmd, env=env, check=True)
    size = DUMP_PATH.stat().st_size
    print(f"OK — {size/1024:.0f} KiB written. Move the project folder anywhere; "
          "run './run.sh restore' on the new machine.")


def restore() -> None:
    env, dbname = _conn_env()
    if not DUMP_PATH.exists():
        raise FileNotFoundError(f"No snapshot at {DUMP_PATH}. Run a backup first.")
    # --clean --if-exists so an existing DB is overwritten cleanly; the target
    # database itself must already exist (createdb is left to the operator to
    # avoid accidental clobbering).
    cmd = [
        _tool("pg_restore"), "--no-owner", "--no-privileges",
        "--clean", "--if-exists", "-d", dbname, str(DUMP_PATH),
    ]
    print(f"Restoring {DUMP_PATH} -> {dbname}")
    # pg_restore returns non-zero on benign warnings; surface output but don't
    # treat warnings as fatal.
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"pg_restore exited {result.returncode} (often just warnings — "
              "verify the data looks right).")
    else:
        print("OK — database restored.")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"dump", "restore"}:
        print("usage: python -m backend.scripts.db_snapshot {dump|restore}")
        sys.exit(2)
    (dump if sys.argv[1] == "dump" else restore)()


if __name__ == "__main__":
    main()
