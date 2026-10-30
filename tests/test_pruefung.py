"""Plausibilitaetspruefung: findet sie eingebaute Fehler - und schweigt bei sauberen Daten?

Die Testreihen sind SIMULIERT (Lambert-Beer mit Spektrenform aus louvert2.txt).
"""
import numpy as np
import pytest
from conftest import ROH

from messdaten.einlesen import lese_spektren
from messdaten.pruefung import (pruefe_dubletten, pruefe_drift, pruefe_kalibrierung,
                                pruefe_saettigung, pruefe_zuordnung)
from messdaten.simulation import simuliere_reihe

C = np.array([0, 1.36, 2.72, 4.06, 5.38, 6.69, 7.99, 9.28, 10.6]) * 1e-6
SPALTEN = list(range(1, 10))


@pytest.fixture(scope="module")
def form():
    m = lese_spektren(ROH / "louvert2.txt")
    s = m.spektrum(9)
    return m.wellenlaengen, s / s.max()


def arten(befunde):
    return {b.pruefung for b in befunde}


@pytest.mark.parametrize("seed", range(10))
def test_saubere_reihe_ohne_fehlalarm(form, seed):
    wl, f = form
    r = simuliere_reihe(wl, f, C, 52500, seed=seed)
    assert pruefe_kalibrierung(C, r.bei(626), SPALTEN) == []
    assert pruefe_drift(r) == []


@pytest.mark.parametrize("seed", range(5))
def test_ausreisser_wird_gefunden(form, seed):
    wl, f = form
    r = simuliere_reihe(wl, f, C, 52500, ausreisser=(4, 0.04), seed=seed)
    befunde = pruefe_kalibrierung(C, r.bei(626), SPALTEN)
    assert any(b.pruefung == "Ausreißer" and b.spalte == 5 for b in befunde)


@pytest.mark.parametrize("seed", range(5))
def test_saettigung_als_kruemmung(form, seed):
    wl, f = form
    r = simuliere_reihe(wl, f, C * 3, 52500, saettigung=1.2, seed=seed)
    befunde = pruefe_kalibrierung(C * 3, r.bei(626), SPALTEN)
    assert any(b.pruefung == "Linearität" and "flacht ab" in b.text for b in befunde)


def test_drift_wird_gefunden(form):
    wl, f = form
    r = simuliere_reihe(wl, f, C, 52500, drift=0.02)
    assert "Drift" in arten(pruefe_drift(r))


def test_vertauschte_proben_sind_fehler(form):
    wl, f = form
    A = simuliere_reihe(wl, f, C, 52500).bei(626)
    A[[3, 6]] = A[[6, 3]]
    befunde = pruefe_kalibrierung(C, A, SPALTEN)
    assert any(b.stufe == "Fehler" and b.pruefung == "Monotonie" for b in befunde)


def test_saettigungsgrenze():
    befunde = pruefe_saettigung([0.5, 1.49, 1.51], [1, 2, 3], grenze=1.5)
    assert [b.spalte for b in befunde] == [3]


def test_echte_dublette_im_datensatz():
    befunde = pruefe_dubletten(lese_spektren(ROH / "louvert2.txt"), lese_spektren(ROH / "figure2.csv"))
    assert len(befunde) == 1
    assert "figure2.csv Spektrum 5" in befunde[0].text and "louvert2.txt Spektrum 8" in befunde[0].text


def test_spektrum_ohne_konzentration_wird_gemeldet():
    m = lese_spektren(ROH / "loujaune1.txt")
    befunde = pruefe_zuordnung(m, range(1, 10))
    assert [b.spalte for b in befunde] == [10]
