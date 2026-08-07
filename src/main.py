import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APP_VERSION = "1.2.0"

if getattr(sys, "frozen", False):
    _root = os.path.dirname(os.path.abspath(sys.executable))
else:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, ".env"))

from adapters.database.schema import create_tables
create_tables()


def main():
    if "--automated" in sys.argv:
        from usecases.testcase_runner import run_automated_cli
        run_automated_cli()
        return

    from interfaces.window import App
    App().run()


if __name__ == "__main__":
    main()