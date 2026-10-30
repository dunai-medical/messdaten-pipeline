"""MCP-Server: Werkzeuge vorhanden, Ergebnisse korrekt, Zugriff auf andere Dateien gesperrt."""
import asyncio
import json

import pytest

mcp_server = pytest.importorskip("mcp_server")


def rufe(name, **args):
    ergebnis = asyncio.run(mcp_server.mcp.call_tool(name, args))
    return json.loads(ergebnis.content[0].text)


def test_werkzeuge_vorhanden():
    namen = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert namen == {"liste_messreihen", "werte_kalibrierung_aus", "berechne_konzentration",
                     "bestimme_bandenfaktor", "werte_standardaddition_aus", "erstelle_pdf_bericht"}


def test_konzentration_ueber_server():
    r = rufe("berechne_konzentration", datei="louvert2.txt", wellenlaenge_nm=626, absorbanz=0.36)
    assert r["konzentration_mol_l"] == pytest.approx(6.8e-6, rel=0.02)
    assert r["hinweise"] == []


def test_extrapolation_wird_gemeldet():
    r = rufe("berechne_konzentration", datei="louvert2.txt", wellenlaenge_nm=626, absorbanz=0.9)
    assert any("Extrapolation" in h for h in r["hinweise"])


@pytest.mark.parametrize("name", ["../../../etc/passwd", "../mcp_server.py", "/etc/hosts", "gibtsnicht.txt"])
def test_kein_zugriff_ausserhalb_data_raw(name):
    with pytest.raises(Exception):
        rufe("werte_kalibrierung_aus", datei=name, wellenlaenge_nm=626)
