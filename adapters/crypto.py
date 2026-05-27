from pathlib import Path

_KEY_FILE = Path.home() / ".bugula" / "secret.key"


def _key() -> bytes:
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes()
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    from cryptography.fernet import Fernet
    k = Fernet.generate_key()
    _KEY_FILE.write_bytes(k)
    return k


def encrypt(value: str) -> str:
    from cryptography.fernet import Fernet
    return Fernet(_key()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return value
    try:
        from cryptography.fernet import Fernet
        return Fernet(_key()).decrypt(value.encode()).decode()
    except Exception:
        return value  # fallback: value was stored unencrypted (legacy)


# Convenience wrappers for email alert settings

_EMAIL_KEYS = {
    "email_enabled", "email_automated_only",
    "email_smtp_host", "email_smtp_port",
    "email_smtp_user", "email_smtp_pass",
    "email_recipient", "email_use_ssl",
}


def get_email_setting(key: str, default: str = "") -> str:
    from adapters.database.settings import get_setting
    raw = get_setting(key, "")
    if not raw:
        return default
    return decrypt(raw)


def set_email_setting(key: str, value: str) -> None:
    from adapters.database.settings import set_setting
    set_setting(key, encrypt(value))
