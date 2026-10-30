"""Traegt den MCP-Server in die Konfiguration der Claude-Desktop-App ein (macOS).

- legt vorher eine Sicherungskopie an (claude_desktop_config.backup.json)
- aendert nur den Eintrag "messdaten-pipeline" unter "mcpServers"
- alle anderen Einstellungen der App bleiben unveraendert

Aufruf (Claude-App vorher beenden):  .venv/bin/python mcp_in_claude_eintragen.py
"""
import json
import shutil
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent
KONFIG = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"

daten = json.loads(KONFIG.read_text(encoding="utf-8")) if KONFIG.exists() else {}
if KONFIG.exists():
    sicherung = KONFIG.with_name("claude_desktop_config.backup.json")
    shutil.copy2(KONFIG, sicherung)
    print(f"Sicherungskopie: {sicherung}")

daten.setdefault("mcpServers", {})["messdaten-pipeline"] = {
    "command": str(PROJEKT / ".venv" / "bin" / "python"),
    "args": [str(PROJEKT / "mcp_server.py")],
}
KONFIG.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Kontrolle: Datei wieder einlesen
json.loads(KONFIG.read_text(encoding="utf-8"))
print("Eingetragen:", json.dumps(daten["mcpServers"]["messdaten-pipeline"], indent=2))
print("Andere Einstellungen unveraendert:", ", ".join(k for k in daten if k != "mcpServers"))
