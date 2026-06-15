# Project Structure

```
we-will-see/
├── .gitignore                          Excluded files
├── .gitattributes                      Git configuration
├── LICENSE                             License
├── README.md                           Documentation overview
├── Datenbankstruktur.docx              Database schema documentation
│
├── data/                               Runtime data (do not commit)
│   ├── database/
│   │   └── app.db                      SQLite database
│   ├── keys/
│   │   └── secret.key                  Encryption key
│   └── testfiles/                      Sample test files
│
├── docs/
│   ├── conventions/
│   │   ├── git-conventions.md          Commit format and Git rules
│   │   └── python-conventions.md       Python code style
│   ├── env/
│   │   └── example.env                 Environment template
│   ├── guides/
│   │   ├── execution.md                Test execution
│   │   ├── performance.md              Performance notes
│   │   ├── recorder.md                 Session recorder
│   │   └── testcase.md                 Testcase format
│   └── thesis/                         HF diploma thesis
│
└── src/
    ├── main.py                         Application entry point
    ├── app.spec                        PyInstaller configuration
    ├── .env                            Local environment variables
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
    │   │   ├── schema.py               Create tables
    │   │   ├── testcases.py            Read/write testcases
    │   │   ├── testresults.py          Read/write results
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
    │   ├── testcase_writer.py          Save steps as YAML
    │   └── value_resolver.py           Resolve placeholders
    │
    ├── interfaces/
    │   ├── window.py                   Main window and navigation
    │   ├── style/
    │   │   ├── style.yaml              Colors and fonts
    │   │   └── style.py                Apply theme
    │   ├── view/
    │   │   ├── dashboard.py            Test results overview
    │   │   ├── testing.py              Edit and run testcases
    │   │   ├── recording.py            Record session
    │   │   ├── results.py              Display results
    │   │   └── settings.py             Settings
    │   └── helper/
    │       ├── widgets.py              Tooltip, divider, form row
    │       └── utils.py                Categories, results directory
    │
    ├── build/                          PyInstaller build artifacts
    └── dist/                           Compiled .exe file
```
