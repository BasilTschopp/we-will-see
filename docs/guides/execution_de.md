# We Will See — Test Execution

## Ablauf
1. Den/die Testfall/-fälle laden. Wird mehr als ein Testfall gleichzeitig
   ausgewählt, werden ihre Schritte zu einem einzigen sequenziellen Durchlauf
   zusammengeführt, sofern nicht die parallele Ausführung aktiviert ist (siehe
   unten).
2. Einen Browser öffnen.
3. Die Anwendung öffnen und sich optional anmelden.
4. Die Release-/Versionsbezeichnung von der Seite lesen, falls ein
   Release-Selektor konfiguriert ist.
5. Schritte sequenziell ausführen. Jeder `matrix`-Eintrag mit Werteliste in
   `meta` führt die gesamte Schrittliste einmal pro Kombination aus und erzeugt
   einen Ergebnissatz pro Iteration.
6. `OK` oder `ERROR` pro Schritt aufzeichnen, mit Ladezeit und Seitentitel.
7. Ergebnisse speichern.
8. Optional bei Fehlschlag eine E-Mail-Benachrichtigung senden.
9. Den Browser schließen.

## Fehlererkennung
Ein Schritt schlägt fehl, wenn:
- Ein Element nicht gefunden oder nicht sichtbar ist.
- Eine Fehlerseite oder ein Fehler-Schlüsselwort im Titel vorkommt. Die
  Schlüsselwortliste ist unter Settings konfigurierbar (`error_page_keywords`);
  die eingebaute Standardliste deckt englische und deutsche Begriffe ab (404,
  500, 403, "not found", "fehler", "wartungsarbeiten", "nicht erreichbar", …).
- Der Textkörper unter 30 Zeichen liegt (Seite gilt als leer).
- Erwarteter Text auf der Seite fehlt (`assert_text`).
- Eine Weiterleitung auf einen fremden Host erfolgt.

Ein fehlgeschlagener Schritt bricht den Durchlauf nicht von sich aus ab. Zwei
Dinge brechen ihn ab:
- Ein Schritt, dessen `method` fehlt oder nicht erkannt wird, bricht den
  gesamten Durchlauf sofort ab (der Schritt wird zuvor noch als `ERROR`
  aufgezeichnet).
- Ist **Stop on error** in den Settings aktiviert, bricht der Durchlauf nach dem
  ersten `ERROR`-Ergebnis jeglicher Art ab.

## Timeout- und Fehlerbehandlungs-Einstellungen
Konfigurierbar unter Settings:
- **Step timeout** (Sekunden, 0 = deaktiviert) — ein einzelner Schritt wird
  abgebrochen und als `ERROR` aufgezeichnet, wenn er länger als dieser Wert
  läuft.
- **Run timeout** (Minuten, 0 = deaktiviert) — der gesamte Durchlauf wird
  gestoppt, wenn er länger als dieser Wert dauert.
- **Stop on error** — den Durchlauf nach dem ersten fehlgeschlagenen Schritt
  abbrechen (siehe oben).
- **Screenshot on error** — für jeden `ERROR`-Schritt einen Screenshot unter
  `data/screenshots/` speichern.

## Parallele Ausführung
Standardmäßig deaktiviert (Settings-Schalter). Bei Deaktivierung laufen alle
ausgewählten Testfälle sequenziell in einer gemeinsamen Browser-Session und
werden zu einem einzigen Durchlauf zusammengeführt. Bei Aktivierung läuft jeder
ausgewählte Testfall in einem eigenen Thread mit eigener Browser-Session und
eigenem Durchlaufeintrag, alle gleichzeitig.

## Testmatrix
Ein `matrix`-Block unter `meta` kann jede Schrittliste mit Parameterkombinationen
verknüpfen: skalare Werte sind Konstanten, Listenwerte werden über das
kartesische Produkt aller Listenschlüssel expandiert. Jede Kombination wird zu
einem eigenen Durchlauf, mit einem aus den variierenden Werten gebildeten Suffix
(z. B. `... [chrome, de]`), und ihre Werte stehen den Schritten als
`{{key}}`-Platzhalter zur Verfügung (siehe `value_resolver.py`).

## Dynamische Werte
Textfelder von Schritten (`description`, `assert_text`, `input_value`, …) können
zur Laufzeit aufgelöste `{{...}}`-Platzhalter enthalten:
- `{{random(min,max)}}` — eine zufällige Ganzzahl im angegebenen Bereich.
- `{{today}}`, `{{today+N}}`, `{{today-N}}`, optional `{{today+N|<strftime-Format>}}`
  — Standard ist `%d.%m.%Y`.
- `{{name}}` — ein zuvor mit `store_as` erfasster Wert (über `read_value` oder
  `form_input`) oder eine Matrix-Variable.

## Automatisierte Ausführung
Als "Automated" markierte Testfälle können headless ohne GUI ausgeführt werden
über:

```
python main.py --automated
```

Jeder automatisierte Testfall läuft sequenziell in seiner eigenen
Browser-Session; ein Fortschrittsfenster zeigt den Live-Schrittstatus, da kein
sichtbares Browser-Overlay vorhanden ist.

## Technische Details

### Technologie
- **Selenium WebDriver** steuert den Browser; Python `threading.Thread` für
  parallele Durchläufe.
- **Unterstützte Browser**: Chrome (Standard), Edge, Firefox — jeweils optional
  im Privat-/Inkognito-Modus.
- Das Browserfenster wird immer mit 1920 × 1080 geöffnet. Automatisierungsflags
  und der Passwort-Manager werden unterdrückt.
- Seitenlade-Timeout: 30 s. Implizites Warten: 1 s.

### Treiberauflösung
Die passende WebDriver-Binärdatei (chromedriver, msedgedriver, geckodriver) wird
automatisch anhand der Hauptversion des installierten Browsers ermittelt. Unter
Windows kann msedgedriver automatisch heruntergeladen werden, falls keine lokale
Kopie gefunden wird.

### Login
Wenn Zugangsdaten konfiguriert sind, navigiert der Runner zur URL und erkennt
Benutzername-/Passwortfelder über eine Liste gängiger CSS-Selektoren (Fallback:
erstes sichtbares `input[type=text/email]`). Nach dem Absenden wird bis zu 15 s
lang auf eine Weiterleitung weg von der Login-/Auth-Seite gewartet.

### Cookie-Banner-Behandlung
Nach dem Login werden automatisch gängige Cookie-Consent-Selektoren und
Button-Texte ausprobiert. Es ist keine Schrittdefinition erforderlich.

### Warten auf Elemente
Vor der Interaktion mit einem Zielelement (`click`, `form_input`, `assert_text`)
wartet der Runner mit `WebDriverWait` bis zu 10 s darauf, dass das Element
vorhanden und klickbar ist. Bei `link`-Schritten wird nach der Navigation bis zu
10 s auf das Erscheinen des `<body>`-Tags gewartet. So wird sichergestellt, dass
Schritte nicht einfach deshalb fehlschlagen, weil die Seite noch nicht fertig
gerendert ist.

### DOM-Stabilität
Nach jedem Klick oder jeder Navigation wartet der Runner zusätzlich, bis der
DOM-Fingerabdruck (Tag-Anzahl + Klassenlisten-Hash via JS) für 250 ms stabil war,
mit einem maximalen Timeout von 8 s. Das verhindert instabile Ergebnisse bei
Single-Page-Anwendungen.

### Schritttypen
| Methode | Was getestet wird |
|---|---|
| `link` | Direkte URL-Navigation; prüft Fehlertitel, leeren Body, hostübergreifende Weiterleitung |
| `nav_click` | Findet ein Navigations-/Seitenleistenelement anhand des Textes und klickt es |
| `table_row` | Klickt die erste Datenzeile einer Tabelle und prüft auf URL- oder DOM-Änderung |
| `form_input` | Gibt einen Wert in ein Feld anhand CSS-Selektor ein; kann optional eine Submit-Taste senden; kann den eingegebenen Wert über `store_as` erfassen |
| `click` | Klickt ein beliebiges Element anhand CSS-Selektor; kann als `optional` markiert werden, um bei fehlendem Element als `OK` übersprungen statt fehlgeschlagen zu werden |
| `assert_text` | Prüft, dass ein String im Seitenkörper oder einem eingeschränkten Element vorkommt |
| `assert_present` | Prüft, dass ein zum Selektor passendes Element existiert und nicht-leeren Text hat |
| `assert_absent` | Prüft, dass ein zum Selektor passendes Element *nicht* existiert oder leer ist |
| `log_text` | Liest den Text eines Elements und zeichnet ihn im Ergebnis auf, ohne etwas zu prüfen |
| `read_value` | Liest Text/Wert eines Elements und speichert ihn mit `store_as` zur späteren `{{...}}`-Verwendung |
| `wait` | Pausiert die Ausführung für eine angegebene Anzahl Sekunden |
| `foreach` | Iteriert über einen gespeicherten Listenwert (`var`) und führt dessen verschachtelte `steps` einmal pro Element aus |

`modal`-, `tab`- und `pagination`-Schritte aus früheren Versionen werden nicht
mehr unterstützt; sie werden stattdessen mit `click`/`assert_present` und einem
expliziten Selektor nachgebildet.

### Ergebnisspeicherung
Ergebnisse werden in einer lokalen Datenbank gespeichert, standardmäßig SQLite
oder eine externe PostgreSQL-Instanz (konfiguriert über Settings > Database,
siehe `dbconfig.py`). Jeder Durchlauf erhält einen Namen der Form `YY.MM.DD -
HH:MM - <testcase>`, gegebenenfalls mit Matrix-Label-Suffix. Jeder Schritt
speichert Status, Ladezeit in ms, Seitentitel, Fehlerdetail und einen
Zeitstempel.

### Reports
`report_generator.py` erstellt pro Durchlauf (oder pro Auswahl an Durchläufen)
einen eigenständigen HTML-Report, entweder mit der vollständigen Schrittliste
oder nur mit Fehlern, gespeichert unter `data/reports/`.

### E-Mail-Benachrichtigungen
Wenn ein Durchlauf mit mindestens einem ERROR endet, wird eine
Fehler-Benachrichtigung per SMTP versendet. Die E-Mail enthält den
Durchlaufnamen und die Liste der fehlgeschlagenen Schritte. Im CLI-Modus
(`--automated`) werden Benachrichtigungen für jeden fehlschlagenden Testfall
einzeln gesendet.
