"""MCP-Server: gibt Claude Werkzeuge fuer die Messdaten-Pipeline.

Claude rechnet nicht selbst, sondern ruft die gepruefte Auswertung auf.
Start (zum Testen): .venv/bin/python mcp_server.py
In Claude Desktop wird er ueber claude_desktop_config.json gestartet.

Demonstration, kein Medizinprodukt.
"""
from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from messdaten.bericht import erstelle_bericht
from messdaten.einlesen import lese_konzentrationen, lese_spektren
from messdaten.pipeline import bandenfaktor_aus_spektrum, werte_aus
from messdaten.pipeline import werte_standardaddition_aus as werte_standardaddition_aus_pipeline

BASIS = Path(__file__).resolve().parent          # Projektordner, unabhaengig vom Startort
ROHDATEN = BASIS / "data" / "raw"
KONZENTRATIONEN = BASIS / "data" / "konzentrationen.csv"
BERICHTE = BASIS / "berichte"
QUELLE = "Daten: Taralle et al., Emergent Scientist 10, 1 (2026), CC BY 4.0"

mcp = MCPServer(
    "messdaten-pipeline",
    instructions=(
        "Werkzeuge zur Auswertung von UV-Vis-Kalibrierreihen (Demonstration, kein Medizinprodukt). "
        "Rechne Kennwerte nie selbst, sondern nutze die Werkzeuge. Gib Befunde der "
        "Plausibilitaetspruefung immer mit aus. Bewertung und Freigabe trifft der Mensch. "
        "Externe Kalibrierungen mit werte_kalibrierung_aus, Standardadditionen mit "
        "werte_standardaddition_aus. Absorbieren zwei Farbstoffe bei derselben Wellenlaenge, "
        "zuerst bestimme_bandenfaktor nutzen und dann mit Bandenkorrektur rechnen; sonst "
        "darauf hinweisen, dass das Ergebnis den Stoerer enthaelt."
    ),
)
NUR_LESEN = ToolAnnotations(readOnlyHint=True)


def _datei(name: str) -> Path:
    """Nur Dateien aus data/raw zulassen - kein Zugriff auf andere Ordner."""
    pfad = (ROHDATEN / name).resolve()
    if pfad.parent != ROHDATEN.resolve() or not pfad.is_file():
        raise ValueError(f"Unbekannte Datei '{name}'. Verfuegbar: {sorted(p.name for p in ROHDATEN.iterdir())}")
    return pfad


@mcp.tool(annotations=NUR_LESEN)
def liste_messreihen() -> list[dict]:
    """Listet alle Messdateien mit Messbereich, Anzahl Spektren und zugeordnetem Farbstoff."""
    stufen = lese_konzentrationen(KONZENTRATIONEN)
    ergebnis = []
    for pfad in sorted(ROHDATEN.iterdir()):
        m = lese_spektren(pfad)
        eigene = [s for s in stufen if s.datei == pfad.name]
        ergebnis.append({
            "datei": pfad.name,
            "wellenlaengen_nm": [float(m.wellenlaengen.min()), float(m.wellenlaengen.max())],
            "spektren": m.anzahl_spektren,
            "farbstoff": eigene[0].farbstoff if eigene else None,
            "methode": eigene[0].methode if eigene else "keine Konzentrationen (nur qualitativ)",
        })
    return ergebnis


@mcp.tool(annotations=NUR_LESEN)
def werte_kalibrierung_aus(datei: str, wellenlaenge_nm: float, ohne_spektren: list[int] | None = None) -> dict:
    """Kalibriergerade mit Kennwerten (Steigung, R2, RMSE, Nachweis-/Bestimmungsgrenze)
    und allen Befunden der Plausibilitaetspruefung.

    ohne_spektren: Nummern (ab 1) von Spektren, die bewusst ausgeschlossen werden.
    Typische Wellenlaengen: Fast Green FCF 626 nm, Quinoline Yellow 417 nm.
    """
    e = werte_aus(_datei(datei), wellenlaenge_nm, KONZENTRATIONEN, ohne_spalten=tuple(ohne_spektren or ()))
    return e.als_dict()


@mcp.tool(annotations=NUR_LESEN)
def berechne_konzentration(datei: str, wellenlaenge_nm: float, absorbanz: float) -> dict:
    """Rechnet eine gemessene Absorbanz mit der Kalibrierung aus 'datei' in eine Konzentration um.

    Meldet, wenn der Wert unter der Bestimmungsgrenze oder oberhalb der hoechsten
    Kalibrierstufe liegt (Extrapolation).
    """
    e = werte_aus(_datei(datei), wellenlaenge_nm, KONZENTRATIONEN)
    k = e.kalibrierung
    c = (absorbanz - k.achsenabschnitt) / k.steigung
    hinweise = []
    if c < k.bestimmungsgrenze:
        hinweise.append("unter der Bestimmungsgrenze - Wert nur eingeschraenkt aussagekraeftig")
    if c > max(e.konzentrationen):
        hinweise.append("oberhalb der hoechsten Kalibrierstufe - Extrapolation, Probe verduennen")
    return {"konzentration_mol_l": c, "kalibrierung": e.messreihe.datei,
            "hinweise": hinweise, "befunde_der_kalibrierung": [str(b) for b in e.befunde]}


@mcp.tool(annotations=NUR_LESEN)
def bestimme_bandenfaktor(datei: str, spektrum: int, wellenlaenge_stoerbande_nm: float,
                          wellenlaenge_eigenbande_nm: float) -> dict:
    """Bandenfaktor F = A(Stoerbande) / A(Eigenbande) aus einem Spektrum, das NUR den Stoerfarbstoff enthaelt.

    Im Datensatz: figure2.csv Spektrum 1 = Mundspuelung, die nur Fast Green enthaelt
    (abgeleitete Zuordnung, siehe data/QUELLE.md). Fuer Fast Green: Stoerbande 417 nm, Eigenbande 626 nm.
    """
    F = bandenfaktor_aus_spektrum(_datei(datei), spektrum, wellenlaenge_stoerbande_nm, wellenlaenge_eigenbande_nm)
    return {"faktor": F, "quelle": f"{datei}, Spektrum {spektrum}",
            "formel": f"A({wellenlaenge_stoerbande_nm:g} nm) / A({wellenlaenge_eigenbande_nm:g} nm)"}


@mcp.tool(annotations=NUR_LESEN)
def werte_standardaddition_aus(datei: str, wellenlaenge_nm: float, ohne_spektren: list[int] | None = None,
                               stoerer_wellenlaenge_nm: float | None = None,
                               bandenfaktor: float | None = None) -> dict:
    """Standardaddition: Ausgangskonzentration der Probe aus Zugaben bekannter Menge (x-Achsenabschnitt).

    Mit stoerer_wellenlaenge_nm und bandenfaktor wird der Beitrag eines zweiten Farbstoffs
    abgezogen: A_korr = A - F * A(Stoerer). Dann wird zusaetzlich das unkorrigierte Ergebnis
    zum Vergleich ausgegeben. Beispiel Quinoline Yellow in der Mundspuelung:
    datei='Jaune fichier.csv', 417 nm, Stoerer Fast Green bei 626 nm.
    """
    e = werte_standardaddition_aus_pipeline(_datei(datei), wellenlaenge_nm, KONZENTRATIONEN,
                                            ohne_spalten=tuple(ohne_spektren or ()),
                                            stoerer_wellenlaenge=stoerer_wellenlaenge_nm, faktor=bandenfaktor)
    return e.als_dict()


@mcp.tool()
def erstelle_pdf_bericht(datei: str, wellenlaenge_nm: float, ohne_spektren: list[int] | None = None) -> str:
    """Erstellt den PDF-Bericht im Ordner berichte/ und gibt den Pfad zurueck."""
    e = werte_aus(_datei(datei), wellenlaenge_nm, KONZENTRATIONEN, ohne_spalten=tuple(ohne_spektren or ()))
    zusatz = f"_ohne{'-'.join(map(str, ohne_spektren))}" if ohne_spektren else ""
    ziel = BERICHTE / f"{Path(datei).stem}_{wellenlaenge_nm:g}nm{zusatz}.pdf"
    return str(erstelle_bericht(e, ziel, QUELLE))


if __name__ == "__main__":
    mcp.run()
