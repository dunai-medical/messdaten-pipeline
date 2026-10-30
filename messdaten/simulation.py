"""SIMULIERTE Testdaten nach Lambert-Beer - keine Messwerte.

Zweck: Fehler gezielt einbauen und pruefen, ob die Plausibilitaetspruefung sie findet.
Die Spektrenform wird aus einem echten gemessenen Spektrum uebernommen, die
Absorbanzen werden berechnet: A(lambda) = Form(lambda) * epsilon * c (+ Fehler).
"""
from __future__ import annotations

import numpy as np

from .einlesen import Messreihe


def simuliere_reihe(wellenlaengen, form, konzentrationen, steigung, *,
                    rauschen=0.002, ausreisser=None, drift=0.0, saettigung=None,
                    seed=0) -> Messreihe:
    """Erzeugt eine Kalibrierreihe.

    form: Spektrum mit Maximum 1 (z. B. normiertes echtes Spektrum)
    ausreisser: (index, versatz) - Spektrum index bekommt versatz addiert
    drift: Grundlinienanstieg vom ersten zum letzten Spektrum
    saettigung: Absorbanz, ab der die Kurve abflacht (vereinfachtes Streulichtmodell)
    """
    rng = np.random.default_rng(seed)
    wl = np.asarray(wellenlaengen, float)
    spalten = []
    n = len(konzentrationen)
    for i, c in enumerate(konzentrationen):
        A = form * steigung * c
        if saettigung is not None:
            A = saettigung * np.tanh(A / saettigung)   # linear bei kleinem A, flach bei grossem
        A = A + rng.normal(0, rauschen, wl.size)
        A = A + drift * i / max(n - 1, 1)
        if ausreisser and ausreisser[0] == i:
            A = A + ausreisser[1] * form
        spalten.append(A)
    return Messreihe(datei="SIMULIERT", wellenlaengen=wl, absorbanz=np.column_stack(spalten),
                     kopf={"Hinweis": "simulierte Daten"})
