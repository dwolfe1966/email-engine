import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'src'))

from email_platform.main import app  # noqa: E402, F401
