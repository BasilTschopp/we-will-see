import json
import os
import sys

from dotenv import dotenv_values, set_key

_DEFAULTS = {
    "engine": "sqlite",
    "sqlite_path": "",
    "pg_host": "",
    "pg_port": 5432,
    "pg_dbname": "",
    "pg_user": "",
    "pg_password": "",
}

# cfg field -> .env variable name. Kept distinct from APP_DB: APP_DB is a
# real process-environment override (highest priority, set outside the app),
# while DB_SQLITE_PATH is the value managed by Settings > Database and is
# re-read from .env on every load so Save takes effect without a restart.
_ENV_KEYS = {
    "engine": "DB_ENGINE",
    "sqlite_path": "DB_SQLITE_PATH",
    "pg_host": "DB_PG_HOST",
    "pg_port": "DB_PG_PORT",
    "pg_dbname": "DB_PG_DBNAME",
    "pg_user": "DB_PG_USER",
    "pg_password": "DB_PG_PASSWORD",
}


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # __file__ is src/adapters/database/dbconfig.py — go up 3 levels to project root
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))


def _env_path() -> str:
    path = os.path.join(_base_dir(), ".env")
    if not os.path.isfile(path):
        open(path, "a", encoding="utf-8").close()
    return path


def _legacy_json_path() -> str:
    return os.path.join(_base_dir(), "data", "database", "db_config.json")


def _migrate_legacy_json() -> None:
    """One-time migration from the old data/database/db_config.json into .env."""
    path = _legacy_json_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return
    if cfg.get("pg_password"):
        from adapters.encryption.crypto import decrypt
        cfg["pg_password"] = decrypt(cfg["pg_password"])
    save_db_config(cfg)
    os.remove(path)


def load_db_config() -> dict:
    _migrate_legacy_json()
    cfg = dict(_DEFAULTS)
    values = dotenv_values(_env_path())
    for field, env_key in _ENV_KEYS.items():
        value = values.get(env_key)
        if value is not None:
            cfg[field] = value
    try:
        cfg["pg_port"] = int(cfg["pg_port"]) if cfg["pg_port"] not in (None, "") else 5432
    except (TypeError, ValueError):
        cfg["pg_port"] = 5432
    return cfg


def save_db_config(cfg: dict) -> None:
    out = dict(_DEFAULTS)
    out.update(cfg)
    path = _env_path()
    for field, env_key in _ENV_KEYS.items():
        set_key(path, env_key, str(out[field]), quote_mode="never")
