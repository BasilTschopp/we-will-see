import logging
import yaml

from models.models import NavigationItem

log = logging.getLogger("bugula")


def load_testcases(name: str) -> tuple[list[NavigationItem], dict]:
    from adapters.database.testcases import fetch_testcase_yaml
    yaml_text, _ = fetch_testcase_yaml(name)
    if not yaml_text:
        log.warning(f"Testcase not found or empty: {name}")
        return [], {}
    return _parse_yaml_text(yaml_text, name)


def _parse_yaml_text(yaml_text: str,
                     label: str = "") -> tuple[list[NavigationItem], dict]:
    try:
        data = yaml.safe_load(yaml_text)
    except Exception as e:
        log.warning(f"Invalid YAML ({label}): {e}")
        return [], {}

    if not isinstance(data, dict):
        log.warning(f"Invalid YAML structure ({label})")
        return [], {}

    meta  = data.get("meta", {})
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
    log.info(f"Testcase loaded: {label} ({len(items)} items)")
    return items, meta

