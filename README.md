# Messdaten-Pipeline: UV-Vis-Kalibrierung mit Plausibilitätsprüfung und MCP-Server

> **Demonstration, kein Medizinprodukt.** Dieses Projekt zeigt eine Arbeitsweise. Es ist nicht
> validiert und nicht für Entscheidungen über Produkte, Proben oder Patienten bestimmt.

Kalibrierreihen werden im Labor oft von Hand in Excel ausgewertet. Das kostet Zeit, und Fehler
fallen spät auf. Diese Pipeline macht aus den Rohdateien eines Photometers in einem Schritt
einen nachvollziehbaren Bericht und prüft die Messreihe dabei auf typische Fehler. Über einen
**MCP-Server** kann Claude die Auswertung direkt aufrufen: Claude erklärt, die Pipeline rechnet.

## Was die Pipeline kann

| Baustein | Inhalt |
|---|---|
| Einlesen | uneinheitliche Dateien: mit/ohne Dateikopf, Dezimalkomma oder -punkt |
| Kalibrierung | Lambert-Beer-Gerade, R², Residuen, RMSE, Nachweis- und Bestimmungsgrenze |
| Standardaddition | Gehalt einer Probe bei Matrixeffekten, optional mit **Bandenkorrektur** für einen zweiten Farbstoff |
| Plausibilitätsprüfung | Ausreißer, Sättigung/Krümmung, Drift, vertauschte Proben, doppelte Spektren, fehlende Zuordnung |
| Bericht | PDF mit Kennwerten, Befunden, Spektren, Kalibriergerade und Residuen |
| MCP-Server | 6 Werkzeuge für Claude (siehe unten) |

Befunde haben drei Stufen: **Fehler** (Daten können so nicht stimmen), **Warnung** (bitte prüfen),
**Hinweis**. Bewertung und Freigabe bleiben beim Menschen.

## Daten

Öffentliche Messdaten aus C. Taralle et al., *Why matrices matter: investigating dye
quantification in listerine® with UV-Visible spectroscopy*, Emergent Scientist 10, 1 (2026),
<https://doi.org/10.1051/emsci/2026001>. Datensatz: <https://zenodo.org/records/20275891>,
Lizenz CC BY 4.0. Farbstoffe Fast Green FCF und Quinoline Yellow, 350–750 nm; externe
Kalibrierung in Wasser und Standardaddition in einer Mundspülung, die beide Farbstoffe enthält.
Zuordnung der Konzentrationen und abgeleitete Annahmen: [`data/QUELLE.md`](data/QUELLE.md).

## Ergebnis: Nachrechnung des Artikels

| Größe | diese Pipeline | Artikel |
|---|---|---|
| Steigung Fast Green (626 nm) | 52 496 L/mol | 52 690 L/mol |
| Fast Green in der Probe, externe Kalibrierung | 6,81·10⁻⁶ mol/L | 6,8·10⁻⁶ |
| Fast Green, Standardaddition | 7,16·10⁻⁶ | 7,0 ± 0,2·10⁻⁶ |
| Bandenfaktor F = A₄₁₇/A₆₂₆ (Fast Green) | 0,116 | 0,12 |
| Quinoline Yellow, Standardaddition ohne / mit Korrektur | 1,17 / 1,03·10⁻⁵ | 1,20 / 1,00·10⁻⁵ |
| Quinoline Yellow, externe Kalibrierung mit Korrektur | 8,33·10⁻⁶ | 8,30·10⁻⁶ |

**Was die Plausibilitätsprüfung zusätzlich findet**

- Die Kalibrierung von Quinoline Yellow flacht oben ab (Krümmung −0,016 Absorbanz), obwohl
  R² = 0,9999. Werden die Stufen über A = 1,5 entfernt, fällt die nächste Stufe als Ausreißer
  auf: Der lineare Bereich endet vermutlich schon unterhalb von A = 1,5. Das könnte erklären,
  warum die Steigung (35 353 L/mol) etwa 4 % unter dem Artikelwert (3,70·10⁴) liegt – belegt
  ist das nicht.
- Ein Spektrum ist im Datensatz doppelt abgelegt (`figure2.csv` Spektrum 5 = `louvert2.txt` Spektrum 8).

## MCP-Server: Claude ruft die Auswertung auf

| Werkzeug | Zweck |
|---|---|
| `liste_messreihen` | verfügbare Dateien mit Farbstoff, Methode, Messbereich |
| `werte_kalibrierung_aus` | externe Kalibrierung mit Kennwerten und Befunden |
| `berechne_konzentration` | Absorbanz → Konzentration, Warnung bei Extrapolation |
| `bestimme_bandenfaktor` | Anteil eines Störfarbstoffs an einer fremden Wellenlänge |
| `werte_standardaddition_aus` | Standardaddition, optional mit Bandenkorrektur |
| `erstelle_pdf_bericht` | PDF-Bericht im Ordner `berichte/` |

Sicherheit: Der Server läuft **lokal** und liest nur Dateien aus `data/raw` (Zugriff auf andere
Pfade wird abgewiesen, siehe Tests). Rohdaten verlassen den Rechner nicht; an das Sprachmodell
gehen nur die Ergebnisse, die ein Werkzeug zurückgibt.

**Erfahrung aus dem Test:** In der ersten Version fehlte das Werkzeug für die Standardaddition.
Claude hat den Gehalt von Quinoline Yellow daraufhin mit den vorhandenen Werkzeugen ohne
Bandenkorrektur berechnet (11,7 statt 10,3 µmol/L) – plausibel formuliert, fachlich unvollständig.
Gefunden wurde das durch die fachliche Prüfung, nicht durch das Modell. Seitdem gibt es
`werte_standardaddition_aus` und eine Anweisung an Claude, auf überlappende Banden hinzuweisen.

## Installation

```bash
python3 -m venv .venv                     # Python ≥ 3.10 (MCP-Paket)
.venv/bin/pip install -r requirements.txt
```

Hinweise aus der Praxis (macOS):
- Das mitgelieferte Python von Apple (3.9) ist zu alt. Aktuelles Python von python.org
  installieren und die Umgebung damit anlegen, z. B. `python3.14 -m venv .venv`.
- Auf Intel-Macs kann `cryptography` (Abhängigkeit von `mcp`) beim Installieren abbrechen,
  weil pip versucht, es selbst zu bauen. Abhilfe:
  `.venv/bin/pip install --only-binary=cryptography -r requirements.txt`
- Das MCP-Paket ab Version 2 heißt die Server-Klasse `MCPServer` (früher `FastMCP`).

## Benutzung

```bash
.venv/bin/python auswerten.py data/raw/louvert2.txt 626          # Bericht in berichte/
.venv/bin/python auswerten.py data/raw/loujaune1.txt 417 --ohne 8 9
.venv/bin/python beispiel.py                                     # Nachrechnung des Artikels
```

**In Claude Desktop einbinden (macOS):** Claude-App beenden, dann
`.venv/bin/python mcp_in_claude_eintragen.py` ausführen. Das Skript legt eine Sicherungskopie
der Konfiguration an und ergänzt nur den Eintrag `messdaten-pipeline`. App neu starten.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

53 Tests in vier Gruppen:
- **Rechenkern** mit Daten, deren Ergebnis exakt bekannt ist (Gerade, Nachweisgrenze, Standardaddition, Bandenkorrektur)
- **Plausibilitätsprüfung** mit **simulierten** Fehlern (Ausreißer, Sättigung, Drift, vertauschte Proben)
  und je 10 sauberen Reihen, die keinen Fehlalarm auslösen dürfen
- **Nachrechnung des Artikels** mit dokumentierten Toleranzen
- **MCP-Server**: Werkzeuge, Ergebnisse, gesperrter Zugriff außerhalb von `data/raw`

## Aufbau

```
messdaten/einlesen.py    Dateien -> Wellenlängen + Absorbanzmatrix
messdaten/auswertung.py  Kalibrierung, Standardaddition, Bandenkorrektur
messdaten/pruefung.py    Plausibilitätsprüfung
messdaten/simulation.py  SIMULIERTE Testreihen (Lambert-Beer + gezielte Fehler)
messdaten/pipeline.py    Gesamtablauf (von Kommandozeile und MCP-Server genutzt)
messdaten/bericht.py     PDF-Bericht
mcp_server.py            MCP-Server für Claude
```

## Grenzen

- Ein Datensatz, ein Gerät, zwei Farbstoffe; Wiederholmessungen sind nicht veröffentlicht.
  Streuung, Ausreißer und Drift sind deshalb nur mit simulierten Daten getestet.
- Die Zuordnung Datei/Spektrum → Konzentration ist aus dem Artikel abgeleitet (`data/QUELLE.md`).
- Grenzwerte der Prüfungen (Absorbanz 1,5; Ausreißer 4 × Reststreuung; Krümmung 3 × Streuung)
  sind Startwerte für diese Demonstration, keine Normvorgabe. Sie müssen je Gerät und Verfahren
  festgelegt und validiert werden.
- Nachweis- und Bestimmungsgrenze nach dem Ansatz 3,3 · s_y / Steigung bzw. 10 · s_y / Steigung
  aus der Kalibriergeraden.
- Die Bandenkorrektur setzt voraus, dass der Störfarbstoff in Probe und Referenz dasselbe
  Spektrum hat; Matrixeffekte können das verändern.
- Mit Claude (KI-Assistent) entwickelt. Anforderungen, fachliche Prüfung der Ergebnisse und
  Freigabe: Aron Dunai-Kovács.

## Lizenz

Code: MIT (siehe `LICENSE`). Daten: CC BY 4.0 der Autorinnen und Autoren des Artikels.
