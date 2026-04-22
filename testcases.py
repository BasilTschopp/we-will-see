import os
import logging

import yaml

from models import NavigationItem

log = logging.getLogger("bugula")

TESTCASES_DIR = "testcases"


def _get_testcases_dir() -> str:
    import sys
    path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                        TESTCASES_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def load_testcases(path: str) -> tuple[list[NavigationItem], dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        log.warning(f"Invalid YAML file: {path}")
        return [], {}

    meta = data.get("meta", {})
    items = [
        NavigationItem(
            url=tc.get("url", ""),
            method=tc.get("method", "link"),
            description=tc.get("description", ""),
            element_text=tc.get("element_text", ""),
            source_url=tc.get("source_url", ""),
            depth=tc.get("depth", 0),
            selector=tc.get("selector", ""),
            input_value=tc.get("input_value", ""),
            submit_key=tc.get("submit_key", ""),
            assert_text=tc.get("assert_text", ""),
        )
        for tc in data.get("testcases", [])
    ]

    log.info(f"Testcases loaded: {path} ({len(items)} items)")
    return items, meta