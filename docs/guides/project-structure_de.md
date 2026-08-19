# Project Structure

```
we-will-see/
├── .gitignore                          Ausgeschlossene Dateien
├── .gitattributes                      Git-Konfiguration
├── LICENSE                             Lizenz
├── README.md                           Dokumentationsübersicht
├── .env                                Umgebungsvariablen (Root, nicht versioniert)
├── requirements.txt                    Python-Abhängigkeiten
├── We Will See.bat                     venv-basierter Launcher
│
├── data/                               Laufzeitdaten (nicht versionieren)
│   ├── database/
│   │   └── app.db                      SQLite-Datenbank (Standard-Engine)
│   ├── keys/
│   │   └── secret.key                  Verschlüsselungsschlüssel
│   ├── logs/
│   │   └── automated.log               Logdatei für --automated-Läufe
│   ├── reports/                        Generierte HTML/DOCX-Ergebnisberichte
│   ├── screenshots/                    Fehler-Screenshots (falls aktiviert)
│   ├── testfiles/                      Beispiel-Testdateien
│   └── tools/                          Einmalige Wartungsskripte
│
├── docs/
│   ├── conventions/
│   │   ├── git-conventions_en.md       Commit-Format und Git-Regeln (Englisch)
│   │   ├── git-conventions_de.md       Commit-Format und Git-Regeln (Deutsch)
│   │   ├── python-conventions_en.md    Python-Code-Stil (Englisch)
│   │   └── python-conventions_de.md    Python-Code-Stil (Deutsch)
│   ├── env/
│   │   └── example.env                 Umgebungsvorlage
│   └── guides/
│       ├── project-structure_en.md     Projektstruktur (diese Datei, Englisch)
│       ├── project-structure_de.md     Projektstruktur (diese Datei, Deutsch)
│       ├── database_en.md              Schema, Engine-Konfiguration, Verschlüsselung (Englisch)
│       ├── database_de.md              Schema, Engine-Konfiguration, Verschlüsselung (Deutsch)
│       ├── execution_en.md             Testausführung (Englisch)
│       ├── execution_de.md             Testausführung (Deutsch)
│       ├── performance_en.md           Performance-Hinweise (Englisch)
│       ├── performance_de.md           Performance-Hinweise (Deutsch)
│       ├── recorder_en.md              Sitzungsrekorder (Englisch)
│       ├── recorder_de.md              Sitzungsrekorder (Deutsch)
│       ├── testcase_en.md              Testfall-Format (Englisch)
│       └── testcase_de.md              Testfall-Format (Deutsch)
│
└── src/
    ├── main.py                         Einstiegspunkt der Anwendung
    ├── app.spec                        PyInstaller-Konfiguration (onedir-Build)
    ├── WeWillSee.spec                  PyInstaller-Konfiguration (onefile-Build)
    │
    ├── core/
    │   └── core.py                     Dataclasses, Logger, CSS-Selektoren
    │
    ├── adapters/
    │   ├── browser/
    │   │   ├── driver.py               Browser starten/stoppen
    │   │   └── login.py                Login automatisieren
    │   ├── database/
    │   │   ├── connection.py           Datenbankverbindung
    │   │   ├── dbconfig.py             SQLite/PostgreSQL-Engine-Konfiguration
    │   │   ├── schema.py               Tabellen erstellen
    │   │   ├── testcases.py            Testfälle lesen/schreiben
    │   │   ├── testresults.py          Ergebnisse lesen/schreiben, Performance-Abfragen
    │   │   ├── settings.py             App-Einstellungen
    │   │   └── presets.py              URL-Presets
    │   ├── encryption/
    │   │   └── crypto.py               Passwortverschlüsselung
    │   └── notification/
    │       └── email_notifier.py       E-Mail-Benachrichtigungen
    │
    ├── usecases/
    │   ├── testcase_runner.py          Tests ausführen
    │   ├── testcase_recorder.py        Browser-Sitzung aufzeichnen
    │   ├── testcase_reader.py          Testfälle laden und parsen
    │   ├── testcase_writer.py          Testfall-YAML speichern
    │   ├── value_resolver.py           `{{...}}`-Platzhalter auflösen
    │   └── report_generator.py         Vollständige/fehler-only HTML-Reports erstellen
    │
    ├── interfaces/
    │   ├── window.py                   Hauptfenster und Navigation
    │   ├── style/
    │   │   ├── style.yaml              Farben und Schriften
    │   │   └── style.py                Theme anwenden
    │   ├── view/
    │   │   ├── testing.py              Testfälle bearbeiten und ausführen
    │   │   ├── recording.py            Sitzung aufzeichnen
    │   │   ├── results.py              Ergebnisse anzeigen, Reports auslösen
    │   │   ├── performance.py          Laufzeit-Trends pro Release
    │   │   ├── progress_window.py      Live-Fortschritt für Headless-Läufe
    │   │   └── settings.py             Einstellungen
    │   └── helper/
    │       ├── widgets.py              Tooltip, Trenner, Formularzeile
    │       └── utils.py                Kategorien, Ergebnisverzeichnis
    │
    ├── build/                          PyInstaller-Build-Artefakte
    └── dist/                           Kompilierte .exe-Datei
```
