import sys
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJEKT))
ROH = PROJEKT / "data" / "raw"
KONZ = PROJEKT / "data" / "konzentrationen.csv"
