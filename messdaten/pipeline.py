"""Ein Aufruf fuer den ganzen Ablauf: einlesen -> pruefen -> kalibrieren -> Ergebnis.

Diese Funktion nutzen sowohl das Kommandozeilenprogramm als auch der MCP-Server.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .auswertung import (Kalibrierung, Standardaddition, bandenfaktor, bandenkorrektur,
                         kalibriere, standardaddition)
from .einlesen import Messreihe, lese_konzentrationen, lese_spektren
from .pruefung import (Befund, pruefe_drift, pruefe_kalibrierung, pruefe_negativ,
                       pruefe_saettigung, pruefe_zuordnung)


@dataclass
class Ergebnis:
    messreihe: Messreihe
    wellenlaenge: float
    farbstoff: str
    spalten: list[int]
    konzentrationen: list[float]
    absorbanzen: list[float]
    kalibrierung: Kalibrierung
    befunde: list[Befund]

    @property
    def freigabefaehig(self) -> bool:
        """Technisch auswertbar, wenn kein Befund der Stufe Fehler vorliegt.

        Die fachliche Freigabe bleibt beim Menschen - das Programm entscheidet sie nicht.
        """
        return not any(b.stufe == "Fehler" for b in self.befunde)

    def als_dict(self) -> dict:
        k = self.kalibrierung
        return {
            "datei": self.messreihe.datei, "farbstoff": self.farbstoff,
            "wellenlaenge_nm": self.wellenlaenge, "stufen": k.n,
            "steigung_l_pro_mol": k.steigung, "achsenabschnitt": k.achsenabschnitt,
            "r2": k.r2, "reststandardabweichung": k.reststandardabweichung,
            "rmse_absorbanz": k.rmse_absorbanz, "rmse_konzentration_mol_l": k.rmse_konzentration,
            "nachweisgrenze_mol_l": k.nachweisgrenze, "bestimmungsgrenze_mol_l": k.bestimmungsgrenze,
            "befunde": [str(b) for b in self.befunde],
            "technisch_auswertbar": self.freigabefaehig,
        }


def werte_aus(datei: str | Path, wellenlaenge: float,
              konzentrationen: str | Path = "data/konzentrationen.csv",
              fenster: float = 0, ohne_spalten: tuple[int, ...] = ()) -> Ergebnis:
    """Wertet eine Kalibrierreihe aus.

    ohne_spalten: Spektren, die nach Pruefung bewusst ausgeschlossen werden
    (wird im Bericht vermerkt).
    """
    m = lese_spektren(datei)
    stufen = [s for s in lese_konzentrationen(konzentrationen)
              if s.datei == m.datei and s.konzentration is not None and s.spalte not in ohne_spalten]
    if not stufen:
        raise ValueError(f"Keine Konzentrationen fuer {m.datei} in {konzentrationen}")
    if "Standardaddition" in stufen[0].methode:
        raise ValueError(f"{m.datei} ist eine Standardaddition - werte_standardaddition_aus verwenden")
    A_alle = m.bei(wellenlaenge, fenster)
    spalten = [s.spalte for s in stufen]
    c = [s.konzentration for s in stufen]
    A = [float(A_alle[s - 1]) for s in spalten]

    befunde = (pruefe_kalibrierung(c, A, spalten)
               + pruefe_saettigung(A_alle, range(1, m.anzahl_spektren + 1))
               + pruefe_negativ(m) + pruefe_drift(m)
               + pruefe_zuordnung(m, spalten))
    if ohne_spalten:
        befunde.append(Befund("Hinweis", "Ausschluss",
                              f"Spektren {', '.join(map(str, ohne_spalten))} bewusst ausgeschlossen"))
    return Ergebnis(m, wellenlaenge, stufen[0].farbstoff, spalten, c, A, kalibriere(c, A), befunde)


# --- Standardaddition (Messung direkt in der Probe) --------------------------

@dataclass
class ErgebnisStandardaddition:
    messreihe: Messreihe
    wellenlaenge: float
    farbstoff: str
    spalten: list[int]
    zugaben: list[float]
    absorbanzen: list[float]          # verwendete Werte (bei Korrektur: korrigiert)
    ergebnis: Standardaddition
    unkorrigiert: Standardaddition | None
    korrektur: dict | None
    befunde: list[Befund]

    def als_dict(self) -> dict:
        d = {
            "datei": self.messreihe.datei, "farbstoff": self.farbstoff,
            "wellenlaenge_nm": self.wellenlaenge, "punkte": len(self.zugaben),
            "ausgangskonzentration_mol_l": self.ergebnis.ausgangskonzentration,
            "hinweis_konzentration": "bezogen auf die Loesung in der Kuevette vor der ersten Zugabe; eine Verduennung der Probe ist ggf. zurueckzurechnen",
            "steigung_l_pro_mol": self.ergebnis.steigung,
            "achsenabschnitt": self.ergebnis.achsenabschnitt, "r2": self.ergebnis.r2,
            "bandenkorrektur": self.korrektur,
            "befunde": [str(b) for b in self.befunde],
            "technisch_auswertbar": not any(b.stufe == "Fehler" for b in self.befunde),
        }
        if self.unkorrigiert is not None:
            d["ausgangskonzentration_ohne_korrektur_mol_l"] = self.unkorrigiert.ausgangskonzentration
        return d


def bandenfaktor_aus_spektrum(datei: str | Path, spektrum: int,
                              wellenlaenge_stoerbande: float, wellenlaenge_eigenbande: float) -> float:
    """F = A(Stoerbande) / A(Eigenbande) aus einem Spektrum, das NUR den Stoerer enthaelt.

    Beispiel: Fast Green allein -> F = A(417 nm) / A(626 nm).
    """
    m = lese_spektren(datei)
    if not 1 <= spektrum <= m.anzahl_spektren:
        raise ValueError(f"Spektrum {spektrum} gibt es nicht ({m.anzahl_spektren} Spektren in {m.datei})")
    a_eigen = float(m.bei(wellenlaenge_eigenbande)[spektrum - 1])
    if a_eigen <= 0.05:
        raise ValueError(f"Absorbanz der Eigenbande nur {a_eigen:.3f} - zu klein fuer einen stabilen Faktor")
    return bandenfaktor(m.bei(wellenlaenge_stoerbande)[spektrum - 1], a_eigen)


def werte_standardaddition_aus(datei: str | Path, wellenlaenge: float,
                               konzentrationen: str | Path = "data/konzentrationen.csv",
                               ohne_spalten: tuple[int, ...] = (),
                               stoerer_wellenlaenge: float | None = None,
                               faktor: float | None = None) -> ErgebnisStandardaddition:
    """Standardaddition, optional mit Bandenkorrektur fuer einen zweiten Farbstoff.

    Mit Korrektur: A_korr(wellenlaenge) = A(wellenlaenge) - F * A(stoerer_wellenlaenge).
    """
    if (stoerer_wellenlaenge is None) != (faktor is None):
        raise ValueError("Fuer die Bandenkorrektur stoerer_wellenlaenge UND faktor angeben (oder keins von beiden)")
    m = lese_spektren(datei)
    stufen = [s for s in lese_konzentrationen(konzentrationen)
              if s.datei == m.datei and s.konzentration is not None and s.spalte not in ohne_spalten]
    if len(stufen) < 3:
        raise ValueError(f"Zu wenige Zugabestufen fuer {m.datei}")
    if "Standardaddition" not in stufen[0].methode:
        raise ValueError(f"{m.datei} ist keine Standardaddition ({stufen[0].methode}) - werte_aus verwenden")

    spalten = [s.spalte for s in stufen]
    x = [s.konzentration for s in stufen]
    A_alle = m.bei(wellenlaenge)
    A = np.array([A_alle[s - 1] for s in spalten])
    unkorr = None
    korrektur = None
    if faktor is not None:
        A_stoer = np.array([m.bei(stoerer_wellenlaenge)[s - 1] for s in spalten])
        unkorr = standardaddition(x, A)
        A = bandenkorrektur(A, A_stoer, faktor)
        korrektur = {"stoerer_wellenlaenge_nm": stoerer_wellenlaenge, "faktor": faktor}

    befunde = (pruefe_kalibrierung(x, A, spalten)
               + pruefe_saettigung(A_alle, range(1, m.anzahl_spektren + 1))
               + pruefe_negativ(m) + pruefe_drift(m) + pruefe_zuordnung(m, spalten))
    if ohne_spalten:
        befunde.append(Befund("Hinweis", "Ausschluss",
                              f"Spektren {', '.join(map(str, ohne_spalten))} bewusst ausgeschlossen"))
    return ErgebnisStandardaddition(m, wellenlaenge, stufen[0].farbstoff, spalten, x, A.tolist(),
                                    standardaddition(x, A), unkorr, korrektur, befunde)
