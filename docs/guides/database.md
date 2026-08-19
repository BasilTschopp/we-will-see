# We Will See — Database

The app persists testcases, results, presets and settings in a local relational
database. SQLite is the default and needs no setup; an external PostgreSQL instance
can be used instead. The relevant code is `adapters/database/connection.py` (engine
selection, connection), `adapters/database/dbconfig.py` (engine configuration),
`adapters/database/schema.py` (tables and migrations), and the per-table modules
`testcases.py`, `testresults.py`, `presets.py`, `settings.py`.

## Engine configuration

The engine is chosen and configured via environment variables in the project-root
`.env` file (see `docs/env/example.env`), normally managed through **Settings >
Database** in the app, which writes these keys back on Save:

| Variable | Meaning |
|---|---|
| `DB_ENGINE` | `sqlite` (default) or `postgres`. |
| `DB_SQLITE_PATH` | Path to the SQLite file. Empty means the default location (see below). |
| `DB_PG_HOST`, `DB_PG_PORT`, `DB_PG_DBNAME`, `DB_PG_USER`, `DB_PG_PASSWORD` | PostgreSQL connection parameters. `DB_PG_PORT` defaults to `5432`. |

`APP_DB` is a separate, higher-priority override: a real process-environment variable
(not read from `.env`) that forces a specific SQLite file path regardless of
`DB_SQLITE_PATH`, intended for headless/deployment setups where the app shouldn't
depend on a writable `.env`.

If no explicit SQLite path is set, the database file defaults to
`data/database/app.db` next to the project root (or next to the executable in a
frozen/PyInstaller build). Its parent directory is created automatically.

A legacy `data/database/db_config.json` file (from an older config format) is
migrated into `.env` automatically on first load and then deleted; an encrypted
`pg_password` in that file is decrypted before being written out.

PostgreSQL support requires the `psycopg2-binary` package (in `requirements.txt`);
it is only imported when the engine is actually `postgres`, so a SQLite-only
install doesn't need it.

## Switching engines

Settings > Database lets you pick the engine and, for PostgreSQL, offers a
**Test connection** button (opens and immediately closes a `psycopg2` connection
with the entered values; SQLite has nothing to test). **Save** only writes the
config to `.env` via `save_db_config()` — it does **not** create tables on the new
target. `create_tables()` runs once, at app start (`main.py`). So after switching
engine, restart the app before using it; otherwise the app is now pointed at a
database (e.g. a fresh PostgreSQL instance) without the expected tables.

Switching engines does **not** migrate data: SQLite content stays in the old file
and PostgreSQL starts empty (aside from whatever `create_tables()` creates on the
next restart).

**Backup and restore** (in Settings) only exist for SQLite — they copy the database
file directly via `sqlite3`'s `.backup()` API. The card is hidden entirely when the
configured engine is `postgres`; for PostgreSQL, use your own `pg_dump`/`pg_restore`
workflow outside the app.

## Engine abstraction

`get_connection()` in `connection.py` returns either a plain `sqlite3.Connection`
(with `row_factory = sqlite3.Row` for dict-style row access) or a `_PgConnection`
wrapper around `psycopg2` that mimics the same interface (`execute`,
`executescript`, `commit`, `rollback`, `close`) so the rest of the codebase writes
one set of SQL statements for both engines. The wrapper translates SQLite-specific
syntax on the fly: `?` placeholders become `%s`, and `datetime('now')` becomes
`CURRENT_TIMESTAMP`. `id` columns use `INTEGER PRIMARY KEY AUTOINCREMENT` on SQLite
and `SERIAL PRIMARY KEY` on PostgreSQL.

## Schema

`create_tables()` in `schema.py` runs on every app start (`main.py`), creating
tables if missing and applying idempotent migrations (each wrapped in its own
try/rollback, so re-running against an already-migrated database is a no-op).

### `settings`
Generic key/value store for app-wide settings (categories, error-page keywords,
timeouts, stop-on-error, screenshot-on-error, parallel execution, performance
thresholds, release selector, email alert config, …). See `adapters/database/settings.py`
for the typed getters/setters. Email credentials stored here go through
`crypto.encrypt`/`decrypt` (see below), not the plain value.

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PK | Setting name. |
| `value` | TEXT | Raw string value; typed getters parse/cast as needed. |

### `testcases`
| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `name` | TEXT UNIQUE | Testcase name. |
| `category` | TEXT | For the UI category filter. |
| `yaml_text` | TEXT | The full YAML document (see `docs/guides/testcase.md`). |
| `automated` | INTEGER (bool) | Included in `--automated` headless runs. |
| `comment` | TEXT | Free-text note (migrated in later; not in the original schema). |
| `created`, `updated` | TEXT | Timestamps; `updated` bumped on every save. Renamed from `created_at`/`updated_at` by migration. |

### `presets`
Reusable login/URL presets, offered when creating a new testcase.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `name` | TEXT UNIQUE | |
| `url` | TEXT | Stored as plain text. |
| `username`, `password` | TEXT | Encrypted at rest via `crypto.encrypt`, decrypted on read via `presets.get_preset()`. |

### `testresults`
One row per executed step (not per run); rows sharing the same `run_name` form one
run's step list.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `run_name` | TEXT | `YY.MM.DD - HH:MM - <testcase>`, with a matrix suffix if applicable. Groups steps into a run. |
| `release` | TEXT | Release/version label read from the page at run start, if configured. Added by migration. |
| `status` | TEXT | `OK` or `ERROR`. |
| `error_detail` | TEXT | Failure reason, if any. |
| `url`, `page_title` | TEXT | Page state at the time of the step. |
| `method`, `description`, `element_text`, `source_url` | TEXT | Copied from the executed `NavigationItem`. |
| `http_status` | TEXT | Not currently populated by the runner; reserved. |
| `load_time_ms` | INTEGER | See `docs/guides/performance.md`. |
| `depth` | INTEGER | Crawl-depth metadata. |
| `screenshot_path` | TEXT | Set when "Screenshot on error" is enabled and the step failed. Added by migration. |
| `username` | TEXT | The login username used for the run. Added by migration. |
| `timestamp` | TEXT | Per-step timestamp. |

Per-testcase execution settings (`screenshot_on_error`, `run_timeout`,
`step_timeout`, `stop_on_error`) used to live as columns on `testcases`; a migration
drops them now that these are global Settings values (see `docs/guides/execution.md`).

## Encryption

`adapters/encryption/crypto.py` uses `cryptography.fernet.Fernet` with a key stored
at `data/keys/secret.key`, generated on first use if missing. `encrypt`/`decrypt`
protect preset credentials and any setting stored via `set_email_setting` (SMTP
credentials for failure alerts). Losing or replacing `secret.key` makes previously
encrypted values undecryptable; `decrypt` then logs a warning and returns an empty
string rather than raising.

Credentials embedded directly in a testcase's YAML `meta` block (`username`/`password`)
are **not** encrypted — only values saved as a reusable preset go through this layer.
