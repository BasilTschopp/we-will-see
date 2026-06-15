import os
import sys


def get_categories() -> list[str]:
    from adapters.database.settings import get_categories as _db_cats
    return _db_cats()


def results_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                     "files", "testresults")
    os.makedirs(d, exist_ok=True)
    return d
