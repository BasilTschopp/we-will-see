# We Will See — Recorder
Der Recorder wandelt eine Live-Browser-Sitzung in einen YAML-Testfall um. Statt
Schritte manuell zu definieren, navigiert der Benutzer durch die Zielanwendung;
der Recorder fängt DOM-Ereignisse ab und wandelt sie in das Schrittformat um, das
der Runner für die Wiedergabe benötigt.

## Funktionsweise
Ein JavaScript-Listener wird über `driver.execute_script()` in die aktive Seite
injiziert. Er registriert Event-Handler und puffert erfasste Ereignisse in
`window.__app_events__`. Ein Guard-Flag (`window.__app_listener_attached__`)
verhindert eine doppelte Registrierung.

Erfasste Ereignistypen:

| DOM-Ereignis | Schritttyp | Details |
|---|---|---|
| `click` | `click` | Gefiltert auf Links, Buttons, ARIA-Rollen (`button`, `tab`, `menuitem`), Submit-/Checkbox-/Radio-Inputs. Metadaten: Selektor, `innerText`, `href`, Tag-Name. |
| `change` | `input` | Bei `input`, `select`, `textarea`. Metadaten: Selektor, Wert, `type`. Submit-/Button-/Reset-/Image-Inputs werden herausgefiltert. |
| `mouseup` | `assert_text` | Textauswahlen ab 3 Zeichen werden als Kandidaten für Assertions gepuffert (max. 200 Zeichen). |
| `keydown` (Enter/Tab) | `key` | Nur bei Textfeldern; wird mit dem vorangegangenen `input`-Ereignis als `submit_key` in `_events_to_steps` zusammengeführt. |
| `history.pushState` / `popstate` | `navigate` | Erfasst clientseitige Routenwechsel (SPA), nicht nur vollständige Seitenladevorgänge. |

Jedes Ereignisobjekt trägt einen Unix-Millisekunden-Zeitstempel (`ts`) und die
aktuelle `location.href`, welche die Konvertierungs-Pipeline zur Schrittreihenfolge
und zum Einfügen von Wartezeiten verwendet.

### Selektor-Strategie (`bestSelector`)

Der Listener berechnet für jedes Element, mit dem interagiert wurde, einen
CSS-Selektor nach folgender Priorität:

1. `#id` — eindeutig und unabhängig vom Layout
2. Stabiles Attribut: `[data-testid]`, `[data-cy]`, `[name]`, `[aria-label]`
3. Struktureller Pfad: bis zu vier Vorfahren, Geschwister-Unterscheidung über `:nth-of-type(n)`

Positionsbasierte Selektoren werden nur als letztes Mittel erzeugt, da sie bei
DOM-Änderungen brechen.

### Passwort-Maskierung

`input`-Ereignisse bei Feldern mit `type="password"` werden mit `value = "***"`
gepuffert. `_events_to_steps` ersetzt diesen Platzhalter durch einen leeren
String, sodass Klartext-Passwörter niemals in das YAML serialisiert werden.
Zugangsdaten werden stattdessen im `meta`-Block verwaltet und zur Laufzeit separat
injiziert.

## Teil 2 — `SessionRecorder` (Python)

`SessionRecorder` umschließt den Selenium WebDriver und steuert den
Aufnahme-Lebenszyklus.

- **`start()`** — injiziert den Listener über `execute_script`, initialisiert den
  internen Zustand und startet einen Daemon-Thread, der alle `POLL_INTERVAL`
  (0,8 s) `_poll_once` aufruft.
- **`stop()`** — setzt das Stop-Flag, joint den Thread und liest die verbleibenden
  Ereignisse aus `window.__app_events__` aus.
- **`event_count()`** — gibt die Länge der aktuellen Ereignisliste zurück (für den
  GUI-Statuszähler).
- **`to_yaml(...)`** — führt die Konvertierungs-Pipeline aus und serialisiert das
  Ergebnis (siehe Teil 3).

### Poll-Zyklus und Re-Injektion

`_poll_once` führt bei jedem Aufruf zwei Operationen aus:

1. **Navigationserkennung.** Weicht `driver.current_url` von der zuletzt
   gespeicherten URL ab, wird ein synthetisches `navigate`-Ereignis erzeugt und
   der Listener erneut injiziert. Dies ist notwendig, da ein vollständiger
   Seitenladevorgang den JavaScript-Kontext zerstört — ohne Re-Injektion würde
   die Erfassung nach der ersten Navigation stillschweigend stoppen.
2. **Ereignisabfluss.** Ein `execute_script`-Aufruf liest `window.__app_events__`
   aus, setzt das Array auf `[]` zurück und gibt die Ereignisse zurück; diese
   werden an die Python-seitige Ereignisliste angehängt.

Alle WebDriver-Aufrufe im Poll-Zyklus sind mit einem breiten except-Block
abgesichert. Vorübergehende Fehler (Seite mitten in der Navigation, kurzzeitige
Nichtverfügbarkeit des Treibers) werden verworfen, statt die Aufnahme zu beenden.

## Teil 3 — Konvertierungs-Pipeline

`to_yaml(...)` leitet die Ereignisliste durch drei Stufen:

```
_events_to_steps(events) → _deduplicate(steps) → PyYAML-Serialisierung
```

### `_events_to_steps`

Linearer Durchlauf; jedes Ereignis wird auf einen Schritttyp abgebildet:

- **`navigate`** → `link`-Schritt mit `url` (nur bei einer effektiven
  URL-Änderung).
- **`input`** → `form_input`-Schritt mit Selektor und Wert. Folgt unmittelbar ein
  `key`-Ereignis, wird es konsumiert und dem Schritt als `submit_key`
  hinzugefügt. Maskierte Passwörter (`***`) werden zu einem leeren String
  normalisiert.
- **`assert_text`** → `assert_text`-Schritt mit dem ausgewählten Text.
- **`click`** → `link`-Schritt für Anker mit einem `href` ohne `javascript:`;
  andernfalls ein `click`-Schritt mit Selektor und Beschriftungstext.

**Wait-Einfügung.** Für jedes Ereignispaar wird das Zeitdelta berechnet.
Überschreitet es `_MIN_WAIT_MS` (1500 ms), wird ein expliziter `wait`-Schritt
eingefügt. Die Dauer ist `min(delta, _MAX_WAIT_MS)` (Obergrenze: 8000 ms),
gerundet auf eine Nachkommastelle. Dieses Verhalten kann mit `no_wait=True`
vollständig deaktiviert werden.

**`source_url`-Tracking.** Der Konverter verfolgt die zuletzt gesehene URL.
Ändert sich die URL zwischen zwei Schritten, wird `source_url` am Schritt
gesetzt, damit der Runner den Startkontext kennt.

### `_deduplicate`

Zweiter Durchlauf zur Rauschreduzierung:

- Identische aufeinanderfolgende Schritte werden zu einem zusammengefasst.
- Ein `link`-Schritt, der unmittelbar auf einen `link`-Schritt zur selben URL
  folgt, wird verworfen.

### Serialisierung

Die Schritte werden in ein `{meta, testcases}`-Dokument eingebettet und mit
`yaml.dump(..., allow_unicode=True, default_flow_style=False)` serialisiert.
Der `meta`-Block enthält die Basis-URL und — nur wenn explizit angegeben — eine
nicht-standardmäßige Browser-Kennung sowie die Laufzeit-Zugangsdaten.

## Orchestrierung — `run_record(...)`

`run_record(...)` verbindet den `SessionRecorder` mit einer vollständigen
Browser-Sitzung:

1. Instanziiert einen **nicht-headless** Browser über den Browser-Adapter.
2. Führt den Login-Ablauf aus, falls Zugangsdaten angegeben wurden; verwendet die
   resultierende URL als Startpunkt.
3. Erstellt einen `SessionRecorder` und ruft `start()` auf.
4. Betreibt einen 1-Hz-Ticker, der `event_count()` an die GUI übermittelt.
5. Fragt `driver.current_url` in der Hauptschleife ab. Eine
   `WebDriverException` signalisiert, dass der Benutzer den Browser geschlossen
   hat — die Schleife wird dann sauber beendet.
6. Ruft `recorder.stop()` und anschließend `to_yaml(...)` mit dem Testfallnamen,
   der URL, der Browser-Kennung und den Zugangsdaten auf.
7. Speichert das YAML über `save_testcase(...)` und sendet ein
   Abschlussereignis an die GUI.

Ein `finally`-Block schließt den Browser und setzt den Laufzustand zurück, sodass
Browser-Abstürze und frühzeitige Abbrüche durch den Benutzer keinen
inkonsistenten Zustand hinterlassen.

## Designentscheidungen

- **Erfassung in JS, Interpretation in Python.** Der injizierte Listener
  erfasst nur rohe DOM-Fakten. Alle Semantiken (Wartezeitschwellen, Zusammenführung
  von Submit-Tasten, Duplikaterkennung) sind in Python implementiert, wo sie
  unit-testbar und ohne Browser-Kontext iterierbar sind.
- **Re-Injektion bei Navigation** ist Voraussetzung dafür, mehrseitige
  Anwendungen vollständig aufzeichnen zu können — nicht nur SPAs mit
  clientseitigem Routing.
- **Stabile Selektoren** und **automatische Wartezeiten** sind die beiden
  wichtigsten Faktoren für eine zuverlässige Wiedergabe: ein Selektor, der bei
  Layoutänderungen bricht, und eine fehlende Wartezeit bei asynchronem Laden
  machen Testfälle nicht-deterministisch.
