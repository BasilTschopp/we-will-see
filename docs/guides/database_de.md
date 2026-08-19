# We Will See — Database

Die App speichert Testfälle, Ergebnisse, Presets und Einstellungen in einer lokalen
relationalen Datenbank. SQLite ist die Standardeinstellung und benötigt keine
Einrichtung; alternativ kann eine externe PostgreSQL-Instanz verwendet werden. Der
relevante Code befindet sich in `adapters/database/connection.py` (Engine-Auswahl,
Verbindung), `adapters/database/dbconfig.py` (Engine-Konfiguration),
`adapters/database/schema.py` (Tabellen und Migrationen) sowie den Modulen pro
Tabelle `testcases.py`, `testresults.py`, `presets.py`, `settings.py`.

## Engine-Konfiguration

Die Engine wird über Umgebungsvariablen in der `.env`-Datei im Projekt-Root
ausgewählt und konfiguriert (siehe `docs/env/example.env`), normalerweise verwaltet
über **Settings > Database** in der App, welche diese Schlüssel beim Speichern
zurückschreibt:

| Variable | Bedeutung |
|---|---|
| `DB_ENGINE` | `sqlite` (Standard) oder `postgres`. |
| `DB_SQLITE_PATH` | Pfad zur SQLite-Datei. Leer bedeutet Standardpfad (siehe unten). |
| `DB_PG_HOST`, `DB_PG_PORT`, `DB_PG_DBNAME`, `DB_PG_USER`, `DB_PG_PASSWORD` | PostgreSQL-Verbindungsparameter. `DB_PG_PORT` ist standardmäßig `5432`. |

`APP_DB` ist ein separater, höher priorisierter Override: eine echte
Prozess-Umgebungsvariable (nicht aus `.env` gelesen), die unabhängig von
`DB_SQLITE_PATH` einen bestimmten SQLite-Dateipfad erzwingt, gedacht für
Headless-/Deployment-Setups, bei denen die App nicht von einer beschreibbaren
`.env` abhängen soll.

Wenn kein expliziter SQLite-Pfad gesetzt ist, verwendet die Datenbankdatei
standardmäßig `data/database/app.db` relativ zum Projekt-Root (bzw. relativ zur
ausführbaren Datei in einem eingefrorenen/PyInstaller-Build). Das übergeordnete
Verzeichnis wird automatisch erstellt.

Eine veraltete `data/database/db_config.json`-Datei (aus einem älteren
Konfigurationsformat) wird beim ersten Laden automatisch nach `.env` migriert und
anschließend gelöscht; ein verschlüsseltes `pg_password` in dieser Datei wird vor
dem Zurückschreiben entschlüsselt.

Die PostgreSQL-Unterstützung erfordert das Paket `psycopg2-binary` (in
`requirements.txt`); es wird nur importiert, wenn die Engine tatsächlich
`postgres` ist, sodass eine reine SQLite-Installation es nicht benötigt.

## Engine wechseln

Unter Settings > Database kann die Engine ausgewählt werden; für PostgreSQL
steht dabei eine Schaltfläche **Test connection** zur Verfügung (öffnet und
schließt sofort wieder eine `psycopg2`-Verbindung mit den eingegebenen Werten;
bei SQLite gibt es nichts zu testen). **Save** schreibt die Konfiguration nur über `save_db_config()` nach
`.env` — es werden **keine** Tabellen auf dem neuen Ziel erstellt. `create_tables()`
läuft einmalig beim App-Start (`main.py`). Nach einem Engine-Wechsel muss die App
also neu gestartet werden, bevor sie verwendet wird; andernfalls zeigt die App auf
eine Datenbank (z. B. eine frische PostgreSQL-Instanz) ohne die erwarteten Tabellen.

Der Engine-Wechsel migriert **keine** Daten: SQLite-Inhalte bleiben in der alten
Datei erhalten, und PostgreSQL startet leer (abgesehen von dem, was
`create_tables()` beim nächsten Neustart anlegt).

**Backup und Restore** (in Settings) existieren nur für SQLite — sie kopieren die
Datenbankdatei direkt über die `.backup()`-API von `sqlite3`. Die Karte wird
komplett ausgeblendet, wenn die konfigurierte Engine `postgres` ist; für
PostgreSQL wird stattdessen ein eigener `pg_dump`/`pg_restore`-Workflow
außerhalb der App benötigt.

## Engine-Abstraktion

`get_connection()` in `connection.py` liefert entweder eine reine
`sqlite3.Connection` (mit `row_factory = sqlite3.Row` für dict-artigen
Zeilenzugriff) oder einen `_PgConnection`-Wrapper um `psycopg2`, der dieselbe
Schnittstelle nachbildet (`execute`, `executescript`, `commit`, `rollback`,
`close`), sodass der Rest der Codebasis einen einzigen Satz an SQL-Anweisungen für
beide Engines schreibt. Der Wrapper übersetzt SQLite-spezifische Syntax on the fly:
`?`-Platzhalter werden zu `%s`, und `datetime('now')` wird zu `CURRENT_TIMESTAMP`.
`id`-Spalten verwenden `INTEGER PRIMARY KEY AUTOINCREMENT` bei SQLite und `SERIAL
PRIMARY KEY` bei PostgreSQL.

## Schema

`create_tables()` in `schema.py` läuft bei jedem App-Start (`main.py`), erstellt
fehlende Tabellen und wendet idempotente Migrationen an (jede in ihrem eigenen
try/rollback gekapselt, sodass ein erneuter Lauf gegen eine bereits migrierte
Datenbank keine Wirkung hat).

### `settings`
Generischer Key/Value-Speicher für app-weite Einstellungen (Kategorien,
Fehlerseiten-Schlüsselwörter, Timeouts, Stop-on-Error, Screenshot-on-Error,
parallele Ausführung, Performance-Schwellenwerte, Release-Selektor,
E-Mail-Alarmkonfiguration, …). Siehe `adapters/database/settings.py` für die
typisierten Getter/Setter. Hier gespeicherte E-Mail-Zugangsdaten durchlaufen
`crypto.encrypt`/`decrypt` (siehe unten), nicht den Klartextwert.

| Spalte | Typ | Anmerkungen |
|---|---|---|
| `key` | TEXT PK | Name der Einstellung. |
| `value` | TEXT | Roher String-Wert; typisierte Getter parsen/casten nach Bedarf. |

### `testcases`
| Spalte | Typ | Anmerkungen |
|---|---|---|
| `id` | PK | |
| `name` | TEXT UNIQUE | Name des Testfalls. |
| `category` | TEXT | Für den Kategoriefilter in der UI. |
| `yaml_text` | TEXT | Das vollständige YAML-Dokument (siehe `docs/guides/testcase_de.md`). |
| `automated` | INTEGER (bool) | In `--automated`-Headless-Läufen enthalten. |
| `comment` | TEXT | Freitext-Notiz (später per Migration hinzugefügt; nicht im ursprünglichen Schema). |
| `created`, `updated` | TEXT | Zeitstempel; `updated` wird bei jedem Speichern aktualisiert. Durch Migration von `created_at`/`updated_at` umbenannt. |

### `presets`
Wiederverwendbare Login-/URL-Presets, die beim Anlegen eines neuen Testfalls
angeboten werden.

| Spalte | Typ | Anmerkungen |
|---|---|---|
| `id` | PK | |
| `name` | TEXT UNIQUE | |
| `url` | TEXT | Als Klartext gespeichert. |
| `username`, `password` | TEXT | Bei der Speicherung über `crypto.encrypt` verschlüsselt, beim Lesen über `presets.get_preset()` entschlüsselt. |

### `testresults`
Eine Zeile pro ausgeführtem Schritt (nicht pro Durchlauf); Zeilen mit demselben
`run_name` bilden zusammen die Schrittliste eines Durchlaufs.

| Spalte | Typ | Anmerkungen |
|---|---|---|
| `id` | PK | |
| `run_name` | TEXT | `YY.MM.DD - HH:MM - <testcase>`, ggf. mit Matrix-Suffix. Gruppiert Schritte zu einem Durchlauf. |
| `release` | TEXT | Release-/Versionsbezeichnung, zu Laufbeginn von der Seite gelesen, falls konfiguriert. Durch Migration hinzugefügt. |
| `status` | TEXT | `OK` oder `ERROR`. |
| `error_detail` | TEXT | Fehlerursache, falls vorhanden. |
| `url`, `page_title` | TEXT | Seitenzustand zum Zeitpunkt des Schritts. |
| `method`, `description`, `element_text`, `source_url` | TEXT | Aus dem ausgeführten `NavigationItem` übernommen. |
| `http_status` | TEXT | Wird derzeit vom Runner nicht befüllt; reserviert. |
| `load_time_ms` | INTEGER | Siehe `docs/guides/performance_de.md`. |
| `depth` | INTEGER | Crawl-Tiefe-Metadaten. |
| `screenshot_path` | TEXT | Gesetzt, wenn "Screenshot on error" aktiviert ist und der Schritt fehlgeschlagen ist. Durch Migration hinzugefügt. |
| `username` | TEXT | Der für den Durchlauf verwendete Login-Benutzername. Durch Migration hinzugefügt. |
| `timestamp` | TEXT | Zeitstempel pro Schritt. |

Die Ausführungseinstellungen pro Testfall (`screenshot_on_error`, `run_timeout`,
`step_timeout`, `stop_on_error`) waren früher Spalten von `testcases`; eine
Migration entfernt sie, da es sich nun um globale Settings-Werte handelt (siehe
`docs/guides/execution_de.md`).

## Verschlüsselung

`adapters/encryption/crypto.py` verwendet `cryptography.fernet.Fernet` mit einem
Schlüssel, der unter `data/keys/secret.key` gespeichert ist und bei Bedarf beim
ersten Gebrauch generiert wird. `encrypt`/`decrypt` schützen Preset-Zugangsdaten
sowie jede über `set_email_setting` gespeicherte Einstellung (SMTP-Zugangsdaten
für Fehleralarme). Der Verlust oder das Ersetzen von `secret.key` macht zuvor
verschlüsselte Werte nicht mehr entschlüsselbar; `decrypt` protokolliert dann eine
Warnung und gibt einen leeren String zurück, statt eine Exception auszulösen.

Zugangsdaten, die direkt im `meta`-Block eines Testfalls in YAML
(`username`/`password`) eingebettet sind, werden **nicht** verschlüsselt — nur
Werte, die als wiederverwendbares Preset gespeichert werden, durchlaufen diese
Schicht.
