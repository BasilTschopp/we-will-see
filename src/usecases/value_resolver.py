import re
import random
from datetime import date, timedelta

_EXPR = re.compile(r"\{\{(.+?)\}\}")


def resolve_input_value(value: str) -> str:
    def _eval(m):
        expr = m.group(1).strip()

        rm = re.fullmatch(r"random\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", expr)
        if rm:
            lo, hi = int(rm.group(1)), int(rm.group(2))
            return str(random.randint(min(lo, hi), max(lo, hi)))

        dm = re.fullmatch(r"today([+-]\d+)?(?:\|(.+))?", expr)
        if dm:
            delta = int(dm.group(1)) if dm.group(1) else 0
            fmt = dm.group(2).strip() if dm.group(2) else "%d.%m.%Y"
            return (date.today() + timedelta(days=delta)).strftime(fmt)

        return m.group(0)

    return _EXPR.sub(_eval, value)
