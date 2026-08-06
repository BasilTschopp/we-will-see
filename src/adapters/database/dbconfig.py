import json
import os
import sys

_DEFAULTS = {
    "engine": "sqlite",
    "sqlite_path": "",
    "pg_host": "",
    "pg_port": 5432,
    "pg_dbname": "",
    "pg_user": "",
    "pg_password": "",
}


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # __file__ is src/adapters/database/dbconfig.py — go up 3 levels to project root
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))


def _config_path() -> str:
    db_dir = os.path.join(_base_dir(), "data", "database")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "db_config.json")


def load_db_config() -> dict:
    cfg = dict(_DEFAULTS)
    path = _config_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    if cfg.get("pg_password"):
        from adapters.encryption.crypto import decrypt
        cfg["pg_password"] = decrypt(cfg["pg_password"])
    return cfg


def save_db_config(cfg: dict) -> None:
    out = dict(_DEFAULTS)
    out.update(cfg)
    if out.get("pg_password"):
        from adapters.encryption.crypto import encrypt
        out["pg_password"] = encrypt(out["pg_password"])
    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
