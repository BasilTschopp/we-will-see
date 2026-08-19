# We Will See — YAML Test Case Format

Ein Testfall wird als einzelnes YAML-Dokument gespeichert. Es ist die zentrale
Schnittstelle des Tools: Der Recorder erzeugt dieses Format, der Runner
konsumiert es, und es ist das, was ein Benutzer bearbeitet, wenn er einen Test
von Hand anpasst. Dieses Dokument beschreibt seinen Aufbau.

Der relevante Code ist `usecases/testcase_reader.py` (Parsing), `core/core.py`
(die Zielstruktur `NavigationItem`) und `usecases/testcase_runner.py`
(Ausführung pro Schritttyp).

## Struktur auf oberster Ebene

Ein Dokument hat genau zwei Schlüssel auf oberster Ebene:

```yaml
meta:
  url: https://example.com
  browser: chrome
  username: alice
  password: secret
testcases:
  - method: link
    url: https://example.com/dashboard
    description: "Open dashboard"
  - method: click
    selector: "#save-button"
    description: "Click save"
```

- **`meta`** — Parameter auf Durchlaufebene (Ziel-URL, Browser, Zugangsdaten,
  Flags, Matrix).
- **`testcases`** — eine geordnete Liste von Schritten. Jeder Listeneintrag wird
  zu einem `NavigationItem` und wird der Reihe nach ausgeführt.

Ist die oberste Ebene keine Zuordnung (Mapping) oder ist das YAML ungültig,
protokolliert der Reader eine Warnung und gibt einen leeren Testfall zurück,
statt eine Exception auszulösen — sodass eine fehlerhafte Datei keinen Durchlauf
zum Absturz bringen kann.

## Der `meta`-Block

Alle Schlüssel sind optional außer `url` (ohne URL bricht der Durchlauf ab).
Werden mehrere Testfälle zu einem Durchlauf kombiniert, werden ihre
`meta`-Blöcke zusammengeführt, wobei spätere Werte gewinnen.

| Schlüssel | Typ | Bedeutung |
|-----|------|---------|
| `url` | string | Ziel-URL der Anwendung. Für einen Durchlauf erforderlich; auch die Login-/Startseite. |
| `browser` | string | `chrome`, `edge` oder `firefox`. Alles andere fällt zurück auf `chrome`. |
| `username` | string | Optionaler Login-Benutzername. |
| `password` | string | Optionales Login-Passwort. |
| `private` | bool | Öffnet den Browser im Privat-/Inkognito-Modus. |
| `matrix` | mapping | Optional. Parametrisiert den Durchlauf: skalare Werte sind Konstanten, Listenwerte werden (kartesisches Produkt) zu je einem Durchlauf pro Kombination expandiert. Siehe unten. |

> Zugangsdaten in `meta` werden so gespeichert, wie sie geschrieben sind. Sie
> werden nur verschlüsselt, wenn sie als wiederverwendbares *Preset* gespeichert
> werden (siehe die Sicherheitsdokumentation), nicht innerhalb des YAML selbst.

### Der `matrix`-Block

```yaml
meta:
  url: https://example.com
  matrix:
    lang: [de, en]
    env: staging
```

Dieses Beispiel erzeugt zwei Durchläufe (`en`/`de`), jeweils mit `env` fest auf
`staging`. Innerhalb der Schritte stehen die Werte der aktuellen Kombination als
`{{lang}}` / `{{env}}`-Platzhalter zur Verfügung (siehe
`usecases/value_resolver.py`). Der Durchlauf-/Ergebnisname erhält ein
`[...]`-Suffix, das aus den variierenden Schlüsseln gebildet wird.

## Die `testcases`-Liste

Jeder Schritt ist eine Zuordnung (Mapping). Das einzige stets bedeutsame Feld
ist `method`, das bestimmt, wie der Schritt ausgeführt wird. Die übrigen Felder
werden mit folgenden Standardwerten in das `NavigationItem` eingelesen:

| Feld | Standard | Verwendet für |
|-------|---------|----------|
| `method` | *(erforderlich)* | Schritttyp (siehe Tabelle unten). Fehlend oder falsch geschrieben → der Schritt schlägt zur Laufzeit mit einem Fehler fehl, statt still auf einen Standard zurückzufallen. |
| `url` | `""` | Ziel-URL für `link`-Schritte. |
| `description` | `""` | Lesbare Bezeichnung, angezeigt in Logs und Ergebnissen. |
| `element_text` | `""` | Sichtbarer Text zum Auffinden eines Elements. |
| `source_url` | `""` | Seite, von der aus der Schritt starten soll, bevor gehandelt wird. |
| `selector` | `""` | CSS-Selektor zum Auffinden eines Elements. |
| `input_value` | `""` | In ein Feld eingegebener Wert, oder die Wartezeit in Sekunden. |
| `submit_key` | `""` | Nach der Eingabe gedrückte Taste (`enter`, `return`, `tab`, `escape`). |
| `assert_text` | `""` | Text, der innerhalb des durch `selector` gefundenen Elements erwartet wird. |
| `depth` | `0` | Crawl-Tiefe-Metadaten (informativ). |
| `store_as` | `""` | Variablenname, unter dem ein erfasster Wert gespeichert wird (`form_input`, `read_value`), für spätere Verwendung mit `{{name}}`. |
| `optional` | `false` | Für `click`: Wenn das Zielelement nicht gefunden wird, wird `OK` (übersprungen) statt `ERROR` aufgezeichnet. |
| `var` | `""` | Nur für `foreach`: die gespeicherte Variable (Liste oder Skalar), über die iteriert wird. Wird zu `foreach_var` geparst. |
| `steps` | `[]` | Nur für `foreach`: verschachtelte Schrittliste, die einmal pro Iteration ausgeführt wird. Wird zu `sub_steps` geparst. |

Jedes Feld, das nicht im YAML vorhanden ist, nimmt einfach seinen Standardwert
an; unbekannte zusätzliche Felder werden ignoriert.

## Schrittmethoden

Der Wert von `method` bestimmt, welche Felder relevant sind. Die folgenden
werden vom Runner erkannt.

| `method` | Zweck | Primäre Felder |
|----------|---------|----------------|
| `link` | Zu einer URL navigieren (behandelt `#`-Hash-Navigation und JS-/OAuth-Weiterleitungen). | `url` |
| `click` | Ein Element per CSS-Selektor klicken. Über `optional` überspringbar. | `selector`, `source_url`, `optional` |
| `form_input` | Einen Wert in ein Feld eingeben, optional mit einer Taste absenden; kann den eingegebenen Wert erfassen. | `selector`, `input_value`, `submit_key`, `source_url`, `store_as` |
| `assert_text` | Prüft, dass Text innerhalb des durch `selector` gefundenen Elements vorhanden ist. | `assert_text` (oder `input_value`), `selector` (erforderlich), `source_url` |
| `assert_present` | Prüft, dass ein zum Selektor passendes Element mit nicht-leerem Text existiert. | `selector`, `source_url` |
| `assert_absent` | Prüft, dass ein zum Selektor passendes Element nicht existiert oder leer ist. | `selector`, `source_url` |
| `log_text` | Liest den Text eines Elements in das Ergebnis, ohne etwas zu prüfen. | `selector` |
| `read_value` | Liest Text/Wert eines Elements und speichert ihn optional. | `selector`, `store_as` |
| `wait` | Pausiert für eine Anzahl Sekunden. | `input_value` (Sekunden) |
| `nav_click` | Klickt ein per sichtbarem Text gefundenes Navigationselement. | `element_text`, `source_url` |
| `table_row` | Klickt die erste Datenzeile einer Tabelle. | `source_url` |
| `foreach` | Führt eine verschachtelte Schrittliste einmal pro Element einer gespeicherten Variable aus. | `var` (→ `foreach_var`), `steps` (→ `sub_steps`) |

`modal`, `tab` und `pagination` aus früheren Versionen wurden entfernt; sie
werden stattdessen mit `click`/`assert_present` und einem expliziten Selektor
nachgebildet.

Ein Schritt, dessen `method` fehlt oder nicht in dieser Liste enthalten ist,
wird als `ERROR`-Ergebnis aufgezeichnet und **bricht den gesamten Durchlauf ab**
(kein Handler wird ausgeführt), statt still übersprungen oder nur als dieser
eine Schritt fehlgeschlagen zu werden.

### Hinweise zu bestimmten Feldern

- **`source_url`** — bei Aktionsschritten (`click`, `form_input`, `nav_click`,
  …) gibt dies an, auf welcher Seite sich der Runner vor der Aktion befinden
  soll. Ist der Browser bereits auf dieser Seite, wird sie nicht neu geladen;
  andernfalls navigiert der Runner zunächst dorthin.
- **`input_value`** — bewusst mehrfach belegt: Es ist der eingegebene Text für
  `form_input` und die Anzahl Sekunden für `wait`.
- **`assert_text`** — der `assert_text`-Handler akzeptiert den erwarteten Text
  entweder in `assert_text` oder `input_value`; `selector` ist erforderlich und
  schränkt die Suche auf den Text dieses Elements ein. Ein fehlender `selector`,
  oder ein `selector`, der innerhalb von 30s auf kein Element passt, wird als
  `ERROR` aufgezeichnet, statt ersatzweise die gesamte Seite zu durchsuchen.
- **`submit_key`** — wird case-insensitiv auf einen echten Tastendruck
  abgebildet. Nicht erkannte Werte werden ignoriert (der Wert wird trotzdem
  eingegeben, nur nicht abgesendet).
- **`store_as`** — schreibt den erfassten Wert in ein durchlaufgebundenes
  Variablen-Dict, gegen das `{{name}}`-Platzhalter (in `description`,
  `assert_text`, `input_value` usw. späterer Schritte) aufgelöst werden. Siehe
  `usecases/value_resolver.py` für die vollständige Platzhaltersyntax,
  einschließlich `{{random(min,max)}}` und `{{today±N}}`.

## Wie der Recorder die Felder befüllt

Wird ein Testfall aufgezeichnet statt von Hand geschrieben, bildet der Recorder
erfasste Browser-Ereignisse auf Schritte ab:

- eine Navigation oder ein Link-Klick mit einem echten `href` → `link` (mit
  `url`)
- ein Nicht-Link-Klick → `click` (mit `selector`, und `source_url`, falls sich
  die Seite geändert hat)
- eine Feldänderung → `form_input` (mit `selector` und `input_value`); ein
  darauffolgendes Enter/Tab wird als `submit_key` zusammengeführt
- eine Textauswahl auf der Seite → `assert_text` (mit dem ausgewählten Text in
  `input_value`)
- eine Pause von mehr als ~1,5 s zwischen Ereignissen → ein expliziter
  `wait`-Schritt

Während der Aufnahme eingegebene Passwörter werden maskiert und nicht in das
YAML geschrieben. Selektoren werden so stabil wie möglich erzeugt (bevorzugt
`id`, dann `data-testid`, `name`, `aria-label`, dann ein kurzer struktureller
Pfad).

## Durchgerechnetes Beispiel

```yaml
meta:
  url: https://shop.example.com
  browser: chrome
  username: testuser
  password: testpass
testcases:
  # 1. Startseite nach dem Login erreichen
  - method: link
    url: https://shop.example.com/
    description: "Startseite öffnen"

  # 2. Produktbereich über die Navigationsleiste öffnen
  - method: nav_click
    element_text: "Products"
    source_url: https://shop.example.com/
    description: "Zu Produkte wechseln"

  # 3. Nach einem Artikel suchen
  - method: form_input
    selector: "#search"
    input_value: "Notebook"
    submit_key: enter
    source_url: https://shop.example.com/products
    description: "Nach Notebook suchen"

  # 4. Den Ergebnissen einen Moment zum Laden geben
  - method: wait
    input_value: "2"
    description: "2s warten"

  # 5. Die erste Ergebniszeile öffnen
  - method: table_row
    source_url: https://shop.example.com/products?q=Notebook
    description: "Erstes Ergebnis öffnen"

  # 6. Bestätigen, dass die Produktseite den erwarteten Text zeigt
  - method: assert_text
    assert_text: "Add to cart"
    description: "Produktseite geladen"
```

Die Ausführung erzeugt ein Ergebnis pro Schritt, jeweils mit Status `OK` oder
`ERROR`, Zeitmessung und (im Fehlerfall) einem Fehlerdetail.

## Validierungsverhalten

Das Format ist bewusst nachsichtig:

- Fehlende optionale Felder nehmen ihre Standardwerte an.
- Ungültiges YAML oder eine oberste Ebene, die kein Mapping ist, ergibt einen
  leeren Testfall (protokolliert als Warnung), keine Exception.
- Eine fehlende oder unbekannte `method` wird zum Ausführungszeitpunkt als
  `ERROR`-Ergebnis aufgezeichnet statt übersprungen, sodass ein vertippter
  Schritttyp im Report auftaucht, statt darin zu verschwinden — bricht dabei
  aber auch den Durchlauf an dieser Stelle ab (siehe oben), sodass die
  verbleibenden Schritte nicht mehr versucht werden.
- Unbekannte zusätzliche Felder (außer `method`) werden ignoriert.
- Ist **Stop on error** in den Settings aktiviert, bricht *jeder*
  fehlschlagende Schritt den Durchlauf ab, nicht nur eine unbekannte `method`.

Das macht das Tool robust: Ein einzelner schlechter Schritt oder ein veraltetes
Feld führt zu einer graduellen Verschlechterung statt zu einem Absturz des
Prozesses, während der fehlerhafte Schritt weiterhin als sichtbarer Fehlschlag
sichtbar bleibt und verhindert wird, dass weitere, wahrscheinlich sinnlose
Schritte gegen einen unerwarteten Seitenzustand ausgeführt werden.
