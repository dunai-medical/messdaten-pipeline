"""Plausibilitaetspruefung von Kalibrierreihen.

Unterscheidet drei Fehlerarten, die man im Labor oft verwechselt:
- Ausreisser: einzelner zufaelliger Fehlwert (z. B. Luftblase, Pipettierfehler)
- Saettigung: Absorbanz so hoch, dass Lambert-Beer nicht mehr gilt
- Systematik: Drift der Grundlinie, Kurve nicht linear, Daten doppelt

Alle Grenzwerte sind Parameter mit Standardwerten. Sie muessen fuer das
jeweilige Geraet und Verfahren festgelegt werden; die Standardwerte sind
Startwerte fuer diese Demonstration, keine Normvorgabe.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .auswertung import kalibriere
from .einlesen import Messreihe

FEHLER, WARNUNG, HINWEIS = "Fehler", "Warnung", "Hinweis"


@dataclass
class Befund:
    stufe: str      # Fehler / Warnung / Hinweis
    pruefung: str   # Kurzname der Pruefung
    text: str
    spalte: int | None = None   # betroffenes Spektrum (ab 1), falls zutreffend

    def __str__(self) -> str:
        ort = f" (Spektrum {self.spalte})" if self.spalte else ""
        return f"[{self.stufe}] {self.pruefung}{ort}: {self.text}"


def pruefe_saettigung(absorbanzen, spalten, grenze=1.5) -> list[Befund]:
    """Absorbanz ueber der Grenze: linearer Bereich vermutlich verlassen."""
    return [
        Befund(WARNUNG, "Sättigung", f"A = {a:.3f} über Warngrenze {grenze} - Linearität in diesem Bereich prüfen, ggf. verdünnen", s)
        for a, s in zip(absorbanzen, spalten) if a > grenze
    ]


def pruefe_negativ(messreihe: Messreihe, von=400, bis=700, grenze=-0.01) -> list[Befund]:
    """Deutlich negative Absorbanz deutet auf falschen Leerwert oder verschmutzte Kuevette."""
    maske = (messreihe.wellenlaengen >= von) & (messreihe.wellenlaengen <= bis)
    minima = messreihe.absorbanz[maske].min(axis=0)
    return [
        Befund(WARNUNG, "Negative Absorbanz", f"Minimum {m:.4f} im Bereich {von}-{bis} nm - Leerwert prüfen", j + 1)
        for j, m in enumerate(minima) if m < grenze
    ]


def pruefe_drift(messreihe: Messreihe, von=720, bis=750, grenze=0.005) -> list[Befund]:
    """Grundlinie in einem Bereich ohne Absorption sollte ueber die Reihe konstant sein.

    Steigt oder faellt sie systematisch von Spektrum zu Spektrum, driftet Lampe oder Detektor.
    """
    maske = (messreihe.wellenlaengen >= von) & (messreihe.wellenlaengen <= bis)
    if not maske.any():
        return [Befund(HINWEIS, "Drift", f"Bereich {von}-{bis} nm nicht gemessen - Drift nicht prüfbar")]
    grundlinie = messreihe.absorbanz[maske].mean(axis=0)
    nicht_leer = np.any(messreihe.absorbanz != 0, axis=0)   # reine Nullspalten = Leerwert
    werte = grundlinie[nicht_leer]
    if len(werte) < 3:
        return []
    steigung = np.polyfit(np.arange(len(werte)), werte, 1)[0]
    gesamt = steigung * (len(werte) - 1)
    if abs(gesamt) > grenze:
        return [Befund(WARNUNG, "Drift", f"Grundlinie {von}-{bis} nm ändert sich über die Reihe um {gesamt:+.4f}")]
    return []


def pruefe_dubletten(*messreihen: Messreihe) -> list[Befund]:
    """Identische Spektren (innerhalb oder zwischen Dateien) - meist Kopierfehler."""
    gesehen: dict[bytes, str] = {}
    befunde = []
    for m in messreihen:
        for j in range(m.anzahl_spektren):
            spalte = m.absorbanz[:, j]
            if not spalte.any():
                continue   # Leerwert aus Nullen ist kein Duplikat
            schluessel = np.round(spalte, 8).tobytes() + str(len(spalte)).encode()
            name = f"{m.datei} Spektrum {j + 1}"
            if schluessel in gesehen:
                befunde.append(Befund(WARNUNG, "Dublette", f"{name} ist identisch mit {gesehen[schluessel]}"))
            else:
                gesehen[schluessel] = name
    return befunde


def pruefe_kalibrierung(konzentrationen, absorbanzen, spalten,
                        r2_min=0.995, ausreisser_faktor=4.0) -> list[Befund]:
    """Pruefungen an der Kalibrierreihe selbst."""
    c = np.asarray(konzentrationen, float)
    A = np.asarray(absorbanzen, float)
    befunde: list[Befund] = []

    # 1. Monotonie: hoehere Konzentration muss hoehere Absorbanz geben
    reihenfolge = np.argsort(c)
    for i, k in zip(reihenfolge[:-1], reihenfolge[1:]):
        if A[k] <= A[i]:
            befunde.append(Befund(FEHLER, "Monotonie",
                                  f"A fällt von {A[i]:.4f} auf {A[k]:.4f}, obwohl c steigt - Verwechslung?", spalten[k]))

    # 2. Ausreisser: jeden Punkt einzeln weglassen, Gerade aus den uebrigen,
    #    Abstand des Punkts in Vielfachen der Reststreuung (robust, weil der
    #    Ausreisser die Vergleichsgerade nicht mitzieht)
    if len(c) >= 5:
        for i in range(len(c)):
            rest = np.arange(len(c)) != i
            kal = kalibriere(c[rest], A[rest])
            abstand = A[i] - (kal.steigung * c[i] + kal.achsenabschnitt)
            if kal.reststandardabweichung > 0 and abs(abstand) > ausreisser_faktor * kal.reststandardabweichung:
                befunde.append(Befund(WARNUNG, "Ausreißer",
                                      f"weicht um {abstand:+.4f} ab ({abs(abstand) / kal.reststandardabweichung:.1f} × Reststreuung)",
                                      spalten[i]))

    # 3. Linearitaet: R2 und Kruemmung (quadratischer Term)
    kal = kalibriere(c, A)
    if kal.r2 < r2_min:
        befunde.append(Befund(WARNUNG, "Linearität", f"R² = {kal.r2:.4f} < {r2_min}"))
    if len(c) >= 5:
        quad = np.polyfit(c, A, 2)
        kruemmung = quad[0] * (c.max() - c.min()) ** 2 / 4   # Abweichung in Bereichsmitte
        # Vergleichsmassstab: Streuung um die Parabel (die Krümmung selbst soll nicht mitzaehlen)
        s_quad = np.sqrt(np.sum((A - np.polyval(quad, c)) ** 2) / (len(c) - 3))
        if abs(kruemmung) > 3 * s_quad and abs(kruemmung) > 0.005:
            art = "flacht ab (Sättigung?)" if quad[0] < 0 else "steigt überproportional"
            befunde.append(Befund(WARNUNG, "Linearität", f"Kurve {art}: Krümmung {kruemmung:+.4f} Absorbanz"))
    return befunde


def pruefe_zuordnung(messreihe: Messreihe, zugeordnete_spalten) -> list[Befund]:
    """Spektren ohne Konzentration werden nicht ausgewertet - sichtbar machen.

    zugeordnete_spalten: nur Spalten, fuer die eine Konzentration bekannt ist.
    Reine Nullspalten (Leerwert) werden nicht gemeldet.
    """
    zugeordnet = set(zugeordnete_spalten)
    return [
        Befund(HINWEIS, "Zuordnung", "Spektrum ohne Konzentrationsangabe - nicht ausgewertet", j + 1)
        for j in range(messreihe.anzahl_spektren)
        if j + 1 not in zugeordnet and messreihe.absorbanz[:, j].any()
    ]
