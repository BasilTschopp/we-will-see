# We Will See

**Python-based test automation tool for web applications.**

Test cases are defined in YAML and can be executed either through the GUI (visible execution) or via the CLI (headless).

---

## Features

- Recording: capture test cases from a live browser session, saved automatically as YAML.
- GUI execution: run tests visually with a browser window.
- CLI execution: run tests headlessly for server-side automation.
- Scheduling: execute automated test cases on a schedule with email alerts on failure.

---

## Getting Started

All commands are run from the `src` folder.

**Run directly:**
```
py main.py
```

**Build a standalone Windows executable:**
```
pyinstaller app.spec
```

`app.spec` is the PyInstaller configuration file. It specifies entry points, bundled assets, and build options to produce a single self-contained `.exe`.

The resulting `we-will-see.exe` is placed in `src/dist/`.

---

## Automation

Test cases marked as automated can be scheduled for server-side execution:

```
py main.py --automated
```

If configured, email alerts are sent automatically on detected failures.

---

## License

Licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).  
Free use, modification, and distribution for non-commercial purposes only.
