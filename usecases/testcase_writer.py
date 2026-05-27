import logging

log = logging.getLogger("bugula")


def save_testcase(name: str, yaml_text: str, category: str = "") -> str:
    from adapters.database.testcases import upsert_testcase
    upsert_testcase(name, yaml_text, category)
    log.info(f"Testcase saved: {name}")
    return name

