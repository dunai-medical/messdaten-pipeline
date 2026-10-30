"""Rechenkern mit Daten, deren richtiges Ergebnis exakt bekannt ist."""
import numpy as np
import pytest

from messdaten.auswertung import (bandenfaktor, bandenkorrektur, kalibriere,
                                  konzentration, standardaddition)


def test_perfekte_gerade():
    c = np.array([0, 1, 2, 3, 4]) * 1e-6
    k = kalibriere(c, 50000 * c + 0.01)
    assert k.steigung == pytest.approx(50000)
    assert k.achsenabschnitt == pytest.approx(0.01)
    assert k.r2 == pytest.approx(1.0)
    assert k.rmse_absorbanz == pytest.approx(0, abs=1e-12)


def test_nachweisgrenze_formel():
    c = np.array([0, 1, 2, 3, 4, 5]) * 1e-6
    A = 40000 * c + np.array([0.002, -0.002, 0.002, -0.002, 0.002, -0.002])
    k = kalibriere(c, A)
    assert k.nachweisgrenze == pytest.approx(3.3 * k.reststandardabweichung / k.steigung)
    assert k.bestimmungsgrenze == pytest.approx(10 * k.reststandardabweichung / k.steigung)
    assert k.bestimmungsgrenze > k.nachweisgrenze


def test_reststandardabweichung_mit_n_minus_2():
    c = np.array([0.0, 1.0, 2.0, 3.0])
    A = np.array([0.0, 1.1, 1.9, 3.0])
    k = kalibriere(c, A)
    assert k.reststandardabweichung == pytest.approx(np.sqrt(np.sum(k.residuen**2) / 2))


def test_rueckrechnung():
    c = np.array([0, 2, 4, 6]) * 1e-6
    k = kalibriere(c, 30000 * c)
    assert konzentration(k, 0.09) == pytest.approx(3e-6)


def test_standardaddition_bekannter_gehalt():
    c0 = 5e-6
    zugaben = np.array([0, 1, 2, 3, 4]) * 1e-6
    sa = standardaddition(zugaben, 30000 * (c0 + zugaben))
    assert sa.ausgangskonzentration == pytest.approx(c0)


def test_bandenkorrektur_entfernt_stoerer():
    F = 0.12
    A_stoerer_eigen = np.array([0.36, 0.36, 0.36])
    A_ziel = np.array([0.1, 0.2, 0.3])
    A_gemessen = A_ziel + F * A_stoerer_eigen
    assert bandenkorrektur(A_gemessen, A_stoerer_eigen, F) == pytest.approx(A_ziel)
    assert bandenfaktor(0.0432, 0.36) == pytest.approx(F)


@pytest.mark.parametrize("c,A", [([0, 1], [0, 1]), ([0, 1, 2], [0, 1])])
def test_ungueltige_eingaben(c, A):
    with pytest.raises(ValueError):
        kalibriere(c, A)
