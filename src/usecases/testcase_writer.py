import logging

log = logging.getLogger("app")


def _unique_name(name: str) -> str:
    from adapters.database.testcases import list_testcases
    existing = {n for n, _ in list_testcases()}
    if name not in existing:
        return name
    counter = 2
    while f"{name} - {counter}" in existing:
        counter += 1
    return f"{name} - {counter}"


def save_testcase(name: str, yaml_text: str, category: str = "") -> str:
    from adapters.database.testcases import upsert_testcase
    unique = _unique_name(name)
    upsert_testcase(unique, yaml_text, category)
    log.info(f"Testcase saved: {unique}")
    return unique

