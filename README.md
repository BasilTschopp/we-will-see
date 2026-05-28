**We Will See**
Python-based test automation tool for web applications. 
Test cases are defined in YAML and can be executed either through the GUI (visible execution) or via the CLI (headless).


**Recording**
Test cases can be recorded from a live browser session and are automatically saved as YAML format.

**Automation**
Test cases marked as automated can be executed using `main.py --automated` for scheduled server-side execution. 
If configured, email alerts are sent automatically on detected failures.

**Execution**
Run directly with `py main.py` or package into a standalone executable.
This is possible using PyInstaller with the provided app.spec.

**License**
This project is licensed under the PolyForm Noncommercial License.
It permits free use, modification, and distribution for non-commercial purposes only.
[PolyForm Noncommercial License 1.0.0](docs/LICENSE)

**Further Documentation**
[Python Conventions](docs/conventions-python.md)
[Git Conventions](docs/conventions-git.md)
[Environment Variables](docs/example.env)
