import os
from pathlib import Path

KEY_PATH = Path(os.getenv("BANK_KEY_PATH", "/run/bank-identity/key"))
