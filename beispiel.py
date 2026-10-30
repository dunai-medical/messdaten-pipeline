"""Beispiel: kompletter Durchlauf mit den Daten aus Taralle et al. (2026), CC BY 4.0."""
from messdaten.einlesen import lese_spektren, lese_konzentrationen
from messdaten.auswertung import kalibriere, konzentration, standardaddition, bandenfaktor, bandenkorrektur

ROH = "data/raw/"
stufen = lese_konzentrationen("data/konzentrationen.csv")


def reihe(datei, wellenlaenge):
    m = lese_spektren(ROH + datei)
    gueltig = [s for s in stufen if s.datei == datei and s.konzentration is not None]
    c = [s.konzentration for s in gueltig]
    A = [m.bei(wellenlaenge)[s.spalte - 1] for s in gueltig]
    return m, c, A


def zeige(name, k):
    print(f"\n{name}")
    print(f"  Steigung a        {k.steigung:,.0f} L/mol")
    print(f"  Achsenabschnitt b {k.achsenabschnitt:.4f}")
    print(f"  R²                {k.r2:.5f}")
    print(f"  RMSE Absorbanz    {k.rmse_absorbanz:.4f}")
    print(f"  RMSE Konzentration {k.rmse_konzentration:.2e} mol/L")
    print(f"  Nachweisgrenze    {k.nachweisgrenze:.2e} mol/L")
    print(f"  Bestimmungsgrenze {k.bestimmungsgrenze:.2e} mol/L")
    print(f"  Groesstes Residuum {max(abs(k.residuen)):.4f}")


# 1. Externe Kalibrierungen
_, c, A = reihe("louvert2.txt", 626)
kal_fcf = kalibriere(c, A)
zeige("Fast Green FCF, 626 nm (externe Kalibrierung)", kal_fcf)

_, c, A = reihe("loujaune1.txt", 417)
kal_qy = kalibriere(c, A)
zeige("Quinoline Yellow, 417 nm (externe Kalibrierung)", kal_qy)

# 2. Probe (Mundspuelung) ueber externe Kalibrierung
vert = lese_spektren(ROH + "Vert fichier.csv")
probe_626 = vert.bei(626)[1]          # Spalte 2 = Probe ohne Zugabe
print(f"\nProbe: A(626) = {probe_626:.3f} -> Fast Green {konzentration(kal_fcf, probe_626):.2e} mol/L")

# 3. Standardaddition Fast Green
gueltig = [s for s in stufen if s.datei == "Vert fichier.csv" and s.konzentration is not None]
sa = standardaddition([s.konzentration for s in gueltig], [vert.bei(626)[s.spalte - 1] for s in gueltig])
print(f"Standardaddition Fast Green: c0 = {sa.ausgangskonzentration:.2e} mol/L (R² {sa.r2:.4f})")

# 4. Mischung: Quinoline Yellow bei 417 nm mit Korrektur fuer Fast Green
fig2 = lese_spektren(ROH + "figure2.csv")
F = bandenfaktor(fig2.bei(417)[0], fig2.bei(626)[0])   # Spalte 1 = Mundspuelung nur mit Fast Green
jaune = lese_spektren(ROH + "Jaune fichier.csv")
gueltig = [s for s in stufen if s.datei == "Jaune fichier.csv" and s.konzentration is not None]
A417 = [jaune.bei(417)[s.spalte - 1] for s in gueltig]
A626 = [jaune.bei(626)[s.spalte - 1] for s in gueltig]
x = [s.konzentration for s in gueltig]
ohne = standardaddition(x, A417)
mit = standardaddition(x, bandenkorrektur(A417, A626, F))
print(f"\nBandenfaktor Fast Green F = A417/A626 = {F:.3f}")
print(f"Quinoline Yellow, Standardaddition ohne Korrektur: {ohne.ausgangskonzentration:.2e} mol/L")
print(f"Quinoline Yellow, Standardaddition mit Korrektur:  {mit.ausgangskonzentration:.2e} mol/L")
probe_korr = bandenkorrektur(A417[0], A626[0], F)
print(f"Quinoline Yellow, externe Kalibrierung mit Korrektur: {konzentration(kal_qy, probe_korr):.2e} mol/L")
