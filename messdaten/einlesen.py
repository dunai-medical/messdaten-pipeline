"""Einlesen von UV-Vis-Spektren in ein einheitliches Format.

Die Rohdateien sind uneinheitlich: mal mit Dateikopf, mal ohne, mal mit
Dezimalkomma, mal mit Dezimalpunkt. Dieses Modul macht daraus immer dasselbe:
einen Vektor Wellenlaengen und eine Matrix Absorbanzen (eine Spalte je Spektrum).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_ZAHL = re.compile(r"^-?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?$")


@dataclass
class Messreihe:
    """Eine Datei mit mehreren Spektren, die alle dieselben Wellenlaengen haben."""

    datei: str
    wellenlaengen: np.ndarray          # in nm, Laenge n
    absorbanz: np.ndarray              # Matrix n x k, Spalte j = Spektrum j+1
    kopf: dict = field(default_factory=dict)   # Metadaten aus dem Dateikopf
    kurven: list = field(default_factory=list)  # Kurvennamen, falls vorhanden

    @property
    def anzahl_spektren(self) -> int:
        return self.absorbanz.shape[1]

    def bei(self, wellenlaenge: float, fenster: float = 0) -> np.ndarray:
        """Absorbanz aller Spektren bei einer Wellenlaenge.

        fenster > 0 mittelt ueber wellenlaenge +/- fenster nm (glaettet Rauschen).
        """
        maske = np.abs(self.wellenlaengen - wellenlaenge) <= fenster
        if not maske.any():
            raise ValueError(
                f"{wellenlaenge} nm liegt ausserhalb des Messbereichs "
                f"{self.wellenlaengen.min():g}-{self.wellenlaengen.max():g} nm ({self.datei})"
            )
        return self.absorbanz[maske].mean(axis=0)

    def spektrum(self, spalte: int) -> np.ndarray:
        """Ein einzelnes Spektrum; spalte zaehlt ab 1 wie in konzentrationen.csv."""
        return self.absorbanz[:, spalte - 1]


def _zahl(text: str) -> float:
    return float(text.strip().replace(",", "."))


def _ist_datenzeile(felder: list[str]) -> bool:
    werte = [f.strip() for f in felder if f.strip()]
    return len(werte) >= 2 and all(_ZAHL.match(w) for w in werte)


def _lies_text(pfad: Path) -> str:
    rohdaten = pfad.read_bytes()
    try:
        return rohdaten.decode("utf-8")
    except UnicodeDecodeError:
        return rohdaten.decode("latin-1")


def lese_spektren(pfad: str | Path) -> Messreihe:
    """Liest eine Spektrendatei (Trennzeichen Semikolon).

    Erkennt automatisch Dateikopf (Schluessel: Wert), Kurvennamen und
    Dezimalkomma/-punkt. Wirft ValueError, wenn Datenzeilen unterschiedlich
    viele Werte haben (Hinweis auf beschaedigte Datei).
    """
    pfad = Path(pfad)
    kopf: dict[str, str] = {}
    kurven: list[str] = []
    zeilen: list[list[float]] = []

    for nummer, felder in enumerate(csv.reader(_lies_text(pfad).splitlines(), delimiter=";"), 1):
        if _ist_datenzeile(felder):
            zeilen.append([_zahl(f) for f in felder if f.strip()])
            continue
        erstes = felder[0].strip() if felder else ""
        if not erstes and any("Curve" in f for f in felder):
            kurven = [f.split(":", 1)[-1].strip() for f in felder[1:] if f.strip()]
        elif ":" in erstes:
            schluessel, wert = erstes.split(":", 1)
            kopf[schluessel.strip()] = wert.strip()

    if not zeilen:
        raise ValueError(f"Keine Messwerte gefunden in {pfad.name}")
    laengen = {len(z) for z in zeilen}
    if len(laengen) != 1:
        raise ValueError(f"Ungleich lange Datenzeilen in {pfad.name}: {sorted(laengen)}")

    matrix = np.array(zeilen)
    return Messreihe(
        datei=pfad.name,
        wellenlaengen=matrix[:, 0],
        absorbanz=matrix[:, 1:],
        kopf=kopf,
        kurven=kurven,
    )


@dataclass
class Stufe:
    """Eine Zeile aus konzentrationen.csv."""

    datei: str
    farbstoff: str
    methode: str
    spalte: int
    konzentration: float | None   # mol/L; None = nicht verwendbar (Leerwert o. ae.)
    hinweis: str


def lese_konzentrationen(pfad: str | Path) -> list[Stufe]:
    with open(pfad, encoding="utf-8", newline="") as datei:
        stufen = []
        for z in csv.DictReader(datei, delimiter=";"):
            wert = z["konzentration_mol_l"].strip()
            stufen.append(Stufe(
                datei=z["datei"], farbstoff=z["farbstoff"], methode=z["methode"],
                spalte=int(z["spalte"]),
                konzentration=_zahl(wert) if wert else None,
                hinweis=z["hinweis"],
            ))
    return stufen
