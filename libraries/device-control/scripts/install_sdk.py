"""Run from an extracted offline bundle; install only its local wheelhouse."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11 or newer required")
    wheelhouse = Path(__file__).resolve().parent / "wheels"
    if not wheelhouse.is_dir():
        raise SystemExit("Missing adjacent wheels directory; extract the complete offline ZIP")
    subprocess.run([sys.executable, "-m", "pip", "--disable-pip-version-check", "install", "--no-index", "--find-links", str(wheelhouse), "dgm-device-control==0.5.0"], check=True)


if __name__ == "__main__":
    main()
