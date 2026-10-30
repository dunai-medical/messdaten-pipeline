"""Kalibrierung nach Lambert-Beer und Kennwerte.

Lambert-Beer: A = epsilon * d * c. Bei fester Schichtdicke d ist die
Absorbanz A linear in der Konzentration c: A = a * c + b.
a (Steigung) entspricht epsilon * d, b (Achsenabschnitt) sollte nahe 0 sein.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Kalibrierung:
    steigung: float               # a in Absorbanz pro (mol/L)
    achsenabschnitt: float        # b in Absorbanz
    r2: float                     # Bestimmtheitsmass
    reststandardabweichung: float  # s_y: Streuung der Punkte um die Gerade (Absorbanz)
    rmse_absorbanz: float         # mittlerer Fehler der Absorbanz
    rmse_konzentration: float     # mittlerer Fehler der rueckgerechneten Konzentration (mol/L)
    nachweisgrenze: float         # LOD in mol/L
    bestimmungsgrenze: float      # LOQ in mol/L
    konzentrationen: np.ndarray
    absorbanzen: np.ndarray
    residuen: np.ndarray          # gemessen - Gerade

    @property
    def n(self) -> int:
        return len(self.konzentrationen)


def kalibriere(konzentrationen, absorbanzen) -> Kalibrierung:
    """Lineare Regression A = a*c + b mit Kennwerten.

    Nachweis- und Bestimmungsgrenze aus der Kalibriergeraden:
    LOD = 3,3 * s_y / a,  LOQ = 10 * s_y / a
    (Ansatz "Standardabweichung der Antwort und Steigung", ICH Q2).
    """
    c = np.asarray(konzentrationen, dtype=float)
    A = np.asarray(absorbanzen, dtype=float)
    if len(c) != len(A):
        raise ValueError("Gleich viele Konzentrationen und Absorbanzen noetig")
    if len(c) < 3:
        raise ValueError("Mindestens 3 Stufen fuer eine Kalibrierung noetig")

    a, b = np.polyfit(c, A, 1)
    vorhersage = a * c + b
    residuen = A - vorhersage
    r2 = 1 - np.sum(residuen**2) / np.sum((A - A.mean()) ** 2)
    s_y = np.sqrt(np.sum(residuen**2) / (len(c) - 2))   # n-2: zwei Parameter geschaetzt
    c_zurueck = (A - b) / a

    return Kalibrierung(
        steigung=a, achsenabschnitt=b, r2=r2, reststandardabweichung=s_y,
        rmse_absorbanz=float(np.sqrt(np.mean(residuen**2))),
        rmse_konzentration=float(np.sqrt(np.mean((c_zurueck - c) ** 2))),
        nachweisgrenze=3.3 * s_y / a,
        bestimmungsgrenze=10 * s_y / a,
        konzentrationen=c, absorbanzen=A, residuen=residuen,
    )


def konzentration(kal: Kalibrierung, absorbanz):
    """Rueckrechnung einer Probe: c = (A - b) / a."""
    return (np.asarray(absorbanz, dtype=float) - kal.achsenabschnitt) / kal.steigung


@dataclass
class Standardaddition:
    steigung: float
    achsenabschnitt: float
    r2: float
    ausgangskonzentration: float   # Konzentration in der Probe vor den Zugaben (mol/L)


def standardaddition(zugaben, absorbanzen) -> Standardaddition:
    """Standardaddition: Zugaben bekannter Menge zur Probe.

    Die Gerade schneidet die x-Achse bei -c0; also c0 = b / a.
    Vorteil: Stoereinfluesse der Probe (Matrix) stecken in jedem Punkt.
    """
    x = np.asarray(zugaben, dtype=float)
    A = np.asarray(absorbanzen, dtype=float)
    a, b = np.polyfit(x, A, 1)
    res = A - (a * x + b)
    r2 = 1 - np.sum(res**2) / np.sum((A - A.mean()) ** 2)
    return Standardaddition(steigung=a, achsenabschnitt=b, r2=r2, ausgangskonzentration=b / a)


def bandenfaktor(a_stoerbande, a_eigenbande) -> float:
    """Anteil einer Substanz an einer fremden Wellenlaenge.

    Beispiel: Fast Green absorbiert stark bei 626 nm und schwach bei 417 nm.
    F = A(417) / A(626), gemessen an einer Loesung, die nur Fast Green enthaelt.
    """
    return float(a_stoerbande) / float(a_eigenbande)


def bandenkorrektur(a_gesamt, a_eigenbande_stoerer, faktor: float):
    """Zieht den Beitrag des Stoerers ab: A_korr = A_gesamt - F * A_stoerer(eigene Bande)."""
    return np.asarray(a_gesamt, dtype=float) - faktor * np.asarray(a_eigenbande_stoerer, dtype=float)
