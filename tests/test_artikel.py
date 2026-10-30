"""Nachrechnung der veroeffentlichten Ergebnisse (Taralle et al. 2026, Tabellen 1 und 2).

Diese Tests schlagen an, wenn eine Code-Aenderung die Ergebnisse verschiebt.
Toleranzen: Abweichung zum Artikel wie in der README dokumentiert.
"""
import pytest
from conftest import KONZ, ROH

from messdaten.auswertung import konzentration
from messdaten.pipeline import bandenfaktor_aus_spektrum, werte_aus, werte_standardaddition_aus


@pytest.fixture(scope="module")
def kal_fcf():
    return werte_aus(ROH / "louvert2.txt", 626, KONZ)


@pytest.fixture(scope="module")
def faktor():
    return bandenfaktor_aus_spektrum(ROH / "figure2.csv", 1, 417, 626)


def test_fast_green_kalibrierung(kal_fcf):
    assert kal_fcf.kalibrierung.steigung == pytest.approx(526.9e2, rel=0.01)   # Artikel 526,9e2 L/mol
    assert kal_fcf.kalibrierung.r2 > 0.999
    assert kal_fcf.befunde == []


def test_fast_green_in_probe_extern(kal_fcf):
    assert konzentration(kal_fcf.kalibrierung, 0.36) == pytest.approx(6.8e-6, rel=0.02)


def test_fast_green_standardaddition():
    e = werte_standardaddition_aus(ROH / "Vert fichier.csv", 626, KONZ)
    assert e.ergebnis.ausgangskonzentration == pytest.approx(7.0e-6, abs=0.2e-6)   # Artikel (7,0 +/- 0,2)e-6


def test_bandenfaktor(faktor):
    assert faktor == pytest.approx(0.12, abs=0.005)


def test_quinoline_yellow_standardaddition(faktor):
    ohne = werte_standardaddition_aus(ROH / "Jaune fichier.csv", 417, KONZ)
    mit = werte_standardaddition_aus(ROH / "Jaune fichier.csv", 417, KONZ,
                                     stoerer_wellenlaenge=626, faktor=faktor)
    assert ohne.ergebnis.ausgangskonzentration == pytest.approx(1.20e-5, rel=0.03)
    assert mit.ergebnis.ausgangskonzentration == pytest.approx(1.00e-5, rel=0.05)
    assert mit.unkorrigiert.ausgangskonzentration == pytest.approx(ohne.ergebnis.ausgangskonzentration)


def test_quinoline_yellow_extern_mit_korrektur(faktor):
    kal = werte_aus(ROH / "loujaune1.txt", 417, KONZ).kalibrierung
    probe = werte_standardaddition_aus(ROH / "Jaune fichier.csv", 417, KONZ)
    A417, A626 = probe.messreihe.bei(417)[1], probe.messreihe.bei(626)[1]
    assert konzentration(kal, A417 - faktor * A626) == pytest.approx(8.30e-6, rel=0.02)


def test_methoden_werden_nicht_verwechselt():
    with pytest.raises(ValueError, match="Standardaddition"):
        werte_aus(ROH / "Vert fichier.csv", 626, KONZ)
    with pytest.raises(ValueError, match="keine Standardaddition"):
        werte_standardaddition_aus(ROH / "louvert2.txt", 626, KONZ)
