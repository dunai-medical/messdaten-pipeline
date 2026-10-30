"""Einlesen: beide Dateiformate, Fehlerfaelle."""
import numpy as np
import pytest
from conftest import ROH, KONZ

from messdaten.einlesen import lese_konzentrationen, lese_spektren


def test_datei_mit_kopf_und_dezimalkomma():
    m = lese_spektren(ROH / "Vert fichier.csv")
    assert m.anzahl_spektren == 10
    assert m.wellenlaengen[0] == 350 and m.wellenlaengen[-1] == 750
    assert m.kopf["Step"] == "1 nm"
    assert m.bei(626)[1] == pytest.approx(0.359504, abs=1e-6)   # Dezimalkomma korrekt gelesen


def test_datei_ohne_kopf_mit_dezimalpunkt():
    m = lese_spektren(ROH / "louvert2.txt")
    assert m.anzahl_spektren == 9
    assert m.kopf == {}
    assert np.all(m.spektrum(1) == 0)          # Leerwert


def test_ausserhalb_messbereich(tmp_path):
    m = lese_spektren(ROH / "loujaune1.txt")   # endet bei 654 nm
    with pytest.raises(ValueError, match="ausserhalb"):
        m.bei(700)


def test_ungleich_lange_zeilen_werden_erkannt(tmp_path):
    f = tmp_path / "kaputt.txt"
    f.write_text("400;0.1;0.2\n401;0.1\n")
    with pytest.raises(ValueError, match="Ungleich lange"):
        lese_spektren(f)


def test_leere_datei(tmp_path):
    f = tmp_path / "leer.txt"
    f.write_text("Title: nichts\n")
    with pytest.raises(ValueError, match="Keine Messwerte"):
        lese_spektren(f)


def test_konzentrationen():
    stufen = lese_konzentrationen(KONZ)
    fcf = [s for s in stufen if s.datei == "louvert2.txt"]
    assert len(fcf) == 9 and fcf[-1].konzentration == pytest.approx(1.06e-5)
    ohne = [s for s in stufen if s.datei == "loujaune1.txt" and s.spalte == 10]
    assert ohne[0].konzentration is None       # Spektrum ohne Angabe im Artikel
