# Messdaten-Pipeline: UV-Vis-Kalibrierung mit Plausibilitätsprüfung

> **Demonstration, kein Medizinprodukt.** Dieses Projekt zeigt eine Arbeitsweise.
> Es ist nicht validiert und nicht für Entscheidungen über Produkte, Proben oder Patienten bestimmt.

**Status:** in Arbeit. Fertig: Einlesen, Auswertung, Plausibilitätsprüfung, PDF-Bericht.
Geplant: automatische Tests, MCP-Server (Claude ruft die Auswertung auf), ausführliche Dokumentation.

## Worum geht es

Kalibrierreihen im Labor werden oft von Hand in Excel ausgewertet. Das kostet Zeit und
Fehler fallen spät auf. Diese Pipeline macht aus Rohdateien eines Photometers in einem
Schritt einen nachvollziehbaren Bericht:

1. **Einlesen** uneinheitlicher Dateien (mit/ohne Dateikopf, Dezimalkomma oder -punkt)
2. **Plausibilitätsprüfung**: Ausreißer, Sättigung, Krümmung, Drift, doppelte Spektren, fehlende Zuordnung
3. **Kalibrierung** nach Lambert-Beer: Steigung, R², RMSE, Nachweis- und Bestimmungsgrenze
4. **Standardaddition** und **Bandenkorrektur** für Mischungen zweier Farbstoffe
5. **PDF-Bericht** mit Kennwerten, Befunden und Diagrammen

Bewertung und Freigabe bleiben beim Menschen; das Programm liefert Zahlen und Hinweise.

## Daten

Öffentliche Messdaten aus C. Taralle et al., *Why matrices matter: investigating dye
quantification in listerine® with UV-Visible spectroscopy*, Emergent Scientist 10, 1 (2026),
https://doi.org/10.1051/emsci/2026001 – Datensatz https://zenodo.org/records/20275891,
Lizenz CC BY 4.0. Farbstoffe: Fast Green FCF und Quinoline Yellow, 350–750 nm.
Details und Zuordnung der Konzentrationen: [`data/QUELLE.md`](data/QUELLE.md).

## Ergebnis: Nachrechnung des Artikels

| Größe | diese Pipeline | Artikel |
|---|---|---|
| Fast Green in der Probe (externe Kalibrierung) | 6,81·10⁻⁶ mol/L | 6,8·10⁻⁶ |
| Fast Green (Standardaddition) | 7,16·10⁻⁶ | 7,0 ± 0,2·10⁻⁶ |
| Bandenfaktor F = A₄₁₇/A₆₂₆ | 0,116 | 0,12 |
| Quinoline Yellow, Standardaddition ohne / mit Korrektur | 1,17 / 1,03·10⁻⁵ | 1,20 / 1,00·10⁻⁵ |
| Quinoline Yellow, externe Kalibrierung mit Korrektur | 8,33·10⁻⁶ | 8,30·10⁻⁶ |

Die Plausibilitätsprüfung meldet bei der Quinoline-Yellow-Kalibrierung eine leichte
Abflachung der oberen Stufen und findet ein doppelt abgelegtes Spektrum im Datensatz.

## Benutzung

```bash
pip install -r requirements.txt
python3 auswerten.py data/raw/louvert2.txt 626      # Bericht in berichte/
python3 beispiel.py                                 # Nachrechnung des Artikels
```

## Grenzen

- Nur ein Datensatz, ein Gerät, zwei Farbstoffe; keine Wiederholmessungen veröffentlicht.
- Die Zuordnung Datei → Konzentration ist aus dem Artikel abgeleitet (siehe `data/QUELLE.md`).
- Grenzwerte der Prüfungen (z. B. Absorbanz 1,5, Ausreißer 4 × Reststreuung) sind Startwerte
  für diese Demonstration, keine Normvorgabe; sie müssen je Gerät und Verfahren festgelegt werden.
- Nachweisgrenze nach dem Ansatz 3,3 · s_y / Steigung aus der Kalibriergeraden.
- Mit Claude (KI-Assistent) entwickelt. Anforderungen, fachliche Prüfung der Ergebnisse und Freigabe: Aron Dunai-Kovács.

## Lizenz

Code: MIT (siehe `LICENSE`). Daten: CC BY 4.0 der Autorinnen und Autoren des Artikels.
