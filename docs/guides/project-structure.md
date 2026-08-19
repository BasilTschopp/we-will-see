# Project Structure

```
we-will-see/
├── .gitignore                          Excluded files
├── .gitattributes                      Git configuration
├── LICENSE                             License
├── README.md                           Documentation overview
├── .env                                Environment variables (root, not committed)
├── requirements.txt                    Python dependencies
├── We Will See.bat                     venv-based launcher
│
├── data/                               Runtime data (do not commit)
│   ├── database/
│   │   └── app.db                      SQLite database (default engine)
│   ├── keys/
│   │   └── secret.key                  Encryption key
│   ├── logs/
│   │   └── automated.log               Log file for --automated runs
│   ├── reports/                        Generated HTML/DOCX result reports
│   ├── screenshots/                    Error screenshots (if enabled)
│   ├── testfiles/                      Sample test files
│   └── tools/                          One-off maintenance scripts
│
├── docs/
│   ├── conventions/
│   │   ├── git-conventions.md          Commit format and Git rules
│   │   └── python-conventions.md       Python code style
│   ├── env/
│   │   └── example.env                 Environment template
│   └── guides/
│       ├── project-structure.md        Project structure (this file)
│       ├── database.md                 Schema, engine config, encryption
│       ├── execution.md                Test execution
│       ├── performance.md              Performance notes
│       ├── recorder.md                 Session recorder
│       └── testcase.md                 Testcase format
│
└── src/
    ├── main.py                         Application entry point
    ├── app.spec                        PyInstaller configuration (onedir build)
    ├── WeWillSee.spec                  PyInstaller configuration (onefile build)
    │
    ├── core/
    │   └── core.py                     Dataclasses, logger, CSS selectors
    │
    ├── adapters/
    │   ├── browser/
    │   │   ├── driver.py               Start/stop browser
    │   │   └── login.py                Automate login
    │   ├── database/
    │   │   ├── connection.py           Database connection
    │   │   ├── dbconfig.py             SQLite/PostgreSQL engine config
    │   │   ├── schema.py               Create tables
    │   │   ├── testcases.py            Read/write testcases
    │   │   ├── testresults.py          Read/write results, performance queries
    │   │   ├── settings.py             App settings
    │   │   └── presets.py              URL presets
    │   ├── encryption/
    │   │   └── crypto.py               Password encryption
    │   └── notification/
    │       └── email_notifier.py       Email alerts
    │
    ├── usecases/
    │   ├── testcase_runner.py          Execute tests
    │   ├── testcase_recorder.py        Record browser session
    │   ├── testcase_reader.py          Load and parse testcases
    │   ├── testcase_writer.py          Persist testcase YAML
    │   ├── value_resolver.py           Resolve `{{...}}` placeholders
    │   └── report_generator.py         Build full/errors-only HTML reports
    │
    ├── interfaces/
    │   ├── window.py                   Main window and navigation
    │   ├── style/
    │   │   ├── style.yaml              Colors and fonts
    │   │   └── style.py                Apply theme
    │   ├── view/
    │   │   ├── testing.py              Edit and run testcases
    │   │   ├── recording.py            Record session
    │   │   ├── results.py              Display results, trigger reports
    │   │   ├── performance.py          Per-release duration trends
    │   │   ├── progress_window.py      Live progress for headless runs
    │   │   └── settings.py             Settings
    │   └── helper/
    │       ├── widgets.py              Tooltip, divider, form row
    │       └── utils.py                Categories, results directory
    │
    ├── build/                          PyInstaller build artifacts
    └── dist/                           Compiled .exe file
```
