"""Automatischer PDF-Bericht (A4) mit matplotlib - ohne weitere Pakete."""
from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from .pipeline import Ergebnis

A4 = (8.27, 11.69)
TEXT, TEXT2, GITTER = "#0b0b0b", "#52514e", "#e4e3df"
DATEN = "#2a78d6"                      # Messpunkte (Kategorie-Farbe 1)
AUFFAELLIG = "#e34948"                 # markierte Punkte, immer mit eigener Form + Beschriftung
RAMPE = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
         "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]   # aufsteigende Konzentration
FUSS = "Demonstration, kein Medizinprodukt"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GITTER,
                     "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
                     "axes.spines.top": False, "axes.spines.right": False})


def _fuss(fig, quelle, seite):
    fig.text(0.08, 0.03, f"{FUSS} · {quelle}", fontsize=7, color=TEXT2)
    fig.text(0.92, 0.03, f"Seite {seite}", fontsize=7, color=TEXT2, ha="right")


def _zahl(x, einheit=""):
    """Deutsches Zahlenformat: grosse Zahlen mit Tausenderpunkt, kleine wissenschaftlich."""
    if abs(x) >= 1000:
        text = f"{x:,.0f}".replace(",", ".")
    elif x != 0 and abs(x) < 0.001:
        mant, exp = f"{x:.2e}".split("e")
        text = f"{mant.replace('.', ',')}·$10^{{{int(exp)}}}$"
    else:
        text = f"{x:.3g}".replace(".", ",")
    return f"{text} {einheit}".strip()


def gesamturteil(e: Ergebnis) -> str:
    """Ein Satz, den auch Leser ohne Vorwissen verstehen."""
    fehler = sum(b.stufe == "Fehler" for b in e.befunde)
    warnungen = sum(b.stufe == "Warnung" for b in e.befunde)
    if fehler:
        return "Schwerer Fehler gefunden – Auswertung nicht verwenden."
    if warnungen:
        wort = "Warnung" if warnungen == 1 else "Warnungen"
        return f"Kein schwerer Fehler gefunden. {warnungen} {wort} bitte prüfen, bevor das Ergebnis verwendet wird."
    return "Keine Auffälligkeiten gefunden."


def erstelle_bericht(e: Ergebnis, ziel: str | Path, quelle: str) -> Path:
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    k = e.kalibrierung
    auffaellig = {b.spalte for b in e.befunde if b.spalte and b.pruefung in ("Ausreißer", "Monotonie")}

    with PdfPages(ziel) as pdf:
        # Seite 1: Kennwerte und Befunde
        fig = plt.figure(figsize=A4)
        fig.text(0.08, 0.93, "Auswertebericht Kalibrierreihe", fontsize=16, weight="bold", color=TEXT)
        fig.text(0.08, 0.905, f"{e.farbstoff} · {e.messreihe.datei} · {e.wellenlaenge:g} nm · "
                 f"erstellt {date.today():%d.%m.%Y}", color=TEXT2)

        zeilen = [
            ("Stufen", str(k.n)),
            ("Steigung a", _zahl(k.steigung, "L/mol")),
            ("Achsenabschnitt b", _zahl(k.achsenabschnitt)),
            ("Bestimmtheitsmaß R²", f"{k.r2:.5f}".replace(".", ",")),
            ("Reststandardabweichung s_y", _zahl(k.reststandardabweichung)),
            ("RMSE Absorbanz", _zahl(k.rmse_absorbanz)),
            ("RMSE Konzentration", _zahl(k.rmse_konzentration, "mol/L")),
            ("Nachweisgrenze (3,3·s_y/a)", _zahl(k.nachweisgrenze, "mol/L")),
            ("Bestimmungsgrenze (10·s_y/a)", _zahl(k.bestimmungsgrenze, "mol/L")),
        ]
        y = 0.85
        fig.text(0.08, y, "Kennwerte", fontsize=11, weight="bold", color=TEXT)
        for name, wert in zeilen:
            y -= 0.027
            fig.text(0.08, y, name, color=TEXT2)
            fig.text(0.55, y, wert, color=TEXT)

        y -= 0.05
        fig.text(0.08, y, f"Befunde der Plausibilitätsprüfung ({len(e.befunde)})", fontsize=11,
                 weight="bold", color=TEXT)
        if not e.befunde:
            y -= 0.027
            fig.text(0.08, y, "Keine Auffälligkeiten.", color=TEXT)
        for b in e.befunde:
            y -= 0.027
            fig.text(0.08, y, b.stufe, color=TEXT, weight="bold")
            ort = f" (Spektrum {b.spalte})" if b.spalte else ""
            zeilen_text = textwrap.wrap(f"{b.pruefung}{ort}: {b.text}", 85)
            for i, z in enumerate(zeilen_text):
                fig.text(0.19, y - i * 0.018, z, color=TEXT)
            y -= 0.018 * (len(zeilen_text) - 1)

        y -= 0.06
        fig.text(0.08, y, gesamturteil(e), weight="bold", color=TEXT)
        fig.text(0.08, y - 0.025, "Bewertung und Freigabe erfolgen durch die verantwortliche Person, "
                 "nicht durch dieses Programm.", color=TEXT2)
        _fuss(fig, quelle, 1)
        pdf.savefig(fig)
        plt.close(fig)

        # Seite 2: Diagramme
        fig = plt.figure(figsize=A4)
        fig.text(0.08, 0.95, "Spektren, Kalibriergerade, Residuen", fontsize=13, weight="bold", color=TEXT)
        ax1 = fig.add_axes([0.1, 0.66, 0.82, 0.25])
        ax2 = fig.add_axes([0.1, 0.33, 0.82, 0.25])
        ax3 = fig.add_axes([0.1, 0.10, 0.82, 0.15], sharex=ax2)

        m = e.messreihe
        for i, s in enumerate(e.spalten):
            ax1.plot(m.wellenlaengen, m.spektrum(s), lw=1.4, color=RAMPE[min(i, len(RAMPE) - 1)])
        ax1.axvline(e.wellenlaenge, color=TEXT2, lw=0.8, ls="--")
        ax1.text(e.wellenlaenge, ax1.get_ylim()[1], f" {e.wellenlaenge:g} nm", color=TEXT2, va="top")
        ax1.set_xlabel("Wellenlänge (nm)")
        ax1.set_ylabel("Absorbanz")
        ax1.set_title("Spektren (heller = niedrigere Konzentration)", loc="left", color=TEXT2, fontsize=9)
        ax1.grid(color=GITTER, lw=0.6)

        c = np.array(e.konzentrationen) * 1e6
        A = np.array(e.absorbanzen)
        linie = np.linspace(0, c.max(), 50)
        ax2.plot(linie, k.steigung * linie / 1e6 + k.achsenabschnitt, color=TEXT2, lw=1.2,
                 label=f"A = {_zahl(k.steigung)}·c + {_zahl(k.achsenabschnitt)}, R² = {k.r2:.4f}".replace(".", ","))
        normal = [s not in auffaellig for s in e.spalten]
        ax2.scatter(c[normal], A[normal], s=36, color=DATEN, zorder=3, label="Kalibrierpunkte")
        if not all(normal):
            sel = ~np.array(normal)
            ax2.scatter(c[sel], A[sel], s=60, marker="X", color=AUFFAELLIG, zorder=4, label="auffällig")
            for ci, ai, s in zip(c[sel], A[sel], np.array(e.spalten)[sel]):
                ax2.annotate(f"Spektrum {s}", (ci, ai), textcoords="offset points", xytext=(6, -12), color=TEXT)
        ax2.set_ylabel("Absorbanz")
        ax2.legend(frameon=False, loc="upper left")
        ax2.grid(color=GITTER, lw=0.6)
        plt.setp(ax2.get_xticklabels(), visible=False)

        ax3.axhline(0, color=TEXT2, lw=0.8)
        ax3.vlines(c, 0, k.residuen, color=DATEN, lw=2)
        ax3.scatter(c, k.residuen, s=16, color=DATEN, zorder=3)
        ax3.set_xlabel("Konzentration (µmol/L)")
        ax3.set_ylabel("Residuum")
        ax3.grid(color=GITTER, lw=0.6)
        _fuss(fig, quelle, 2)
        pdf.savefig(fig)
        plt.close(fig)
    return ziel
