# We Will See — Performance Measurement

Dies ist kein klassischer Performance-Test. Die Werte dienen als Indikator: Wenn ein neues Release über mehrere Schritte hinweg eine deutlich höhere Ladezeit im Vergleich zu früheren Durchläufen zeigt, ist das ein Signal, das eine Untersuchung wert ist, nicht eine präzise Messung der Ursache.

## Was wird gemessen
Jeder Testschritt zeichnet einen `load_time_ms`-Wert auf. Der Timer startet zu Beginn
des Step-Handlers und stoppt, sobald das Zielelement gefunden wurde oder die
Navigation abgeschlossen ist, noch vor dem DOM-Stabilitäts-Wait nach der Aktion.

Bei Navigationsschritten (`link`) umfasst dies die Zeit von `driver.get()` bis das
`<body>`-Tag vorhanden ist. Bei Interaktionsschritten (`click`, `nav_click`, `form_input`
usw.) umfasst dies die Elementsuche zuzüglich eines eventuell ausgelösten Seitenladens,
um die Quell-URL zu erreichen.

Der Wert wird in Millisekunden gespeichert und neben jedem Ergebnis angezeigt.

## Performance-Ansicht
`interfaces/view/performance.py` zeigt pro Testfall die gesamte Laufzeit für jedes
Release sowie deren prozentuale Änderung gegenüber dem vorherigen Release und
gegenüber dem ersten erfassten Release. Zeilen werden hervorgehoben, wenn eine
Änderung die konfigurierbaren Alarmschwellen überschreitet (Settings: Performance-
Schwellenwert vs. vorheriges / vs. erstes Release, Prozent, `0` deaktiviert die
jeweilige Prüfung). Die Release-Bezeichnung pro Durchlauf stammt aus einem über
Settings konfigurierten Seitenelement (CSS-Selektor + optionaler Regex), das direkt
nach dem Login ausgelesen wird.

## Was es nicht ist
Die gemessene Zeit ist eine von Selenium erfasste Echtzeitdauer und beinhaltet:

- Selenium-Overhead und Kommunikationslatenz mit dem WebDriver
- Zeit für die Elementsuche (CSS-Selektor-Abgleich über das DOM)
- Alle vom Test-Runner selbst eingeführten Wartezeiten

Sie isoliert nicht die Serverantwortzeit, den Netzwerkdurchsatz oder die Renderzeit.
Es wird keine Last erzeugt. Jeder Durchlauf ist eine einzelne sequenzielle oder
pro Testfall separate Browser-Session. Die Werte eignen sich, um Seiten zu erkennen,
die auffällig langsam sind oder sich zwischen Durchläufen verschlechtern, sollten
aber nicht als Benchmark-Ergebnisse interpretiert werden.
