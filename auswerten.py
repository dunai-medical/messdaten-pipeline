"""Kommandozeile: python3 auswerten.py DATEI WELLENLAENGE [--ohne 10]

Beispiel: python3 auswerten.py data/raw/louvert2.txt 626
"""
import argparse
from pathlib import Path

from messdaten.bericht import erstelle_bericht
from messdaten.pipeline import werte_aus

QUELLE = "Daten: Taralle et al., Emergent Scientist 10, 1 (2026), CC BY 4.0"

p = argparse.ArgumentParser(description="Kalibrierreihe auswerten und PDF-Bericht erstellen")
p.add_argument("datei")
p.add_argument("wellenlaenge", type=float)
p.add_argument("--ohne", type=int, nargs="*", default=[], help="Spektren ausschliessen (Nummern ab 1)")
a = p.parse_args()

e = werte_aus(a.datei, a.wellenlaenge, ohne_spalten=tuple(a.ohne))
for b in e.befunde:
    print(b)
ziel = erstelle_bericht(e, Path("berichte") / f"{Path(a.datei).stem}_{a.wellenlaenge:g}nm.pdf", QUELLE)
print(f"R² = {e.kalibrierung.r2:.5f}, LOD = {e.kalibrierung.nachweisgrenze:.2e} mol/L -> {ziel}")
