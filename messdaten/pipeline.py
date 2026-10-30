"""Ein Aufruf fuer den ganzen Ablauf: einlesen -> pruefen -> kalibrieren -> Ergebnis.

Diese Funktion nutzen sowohl das Kommandozeilenprogramm als auch der MCP-Server.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .auswertung import Kalibrierung, kalibriere
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
