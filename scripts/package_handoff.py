"""Package only the explicitly listed project handoff files and verify bytes."""

from hashlib import sha256
from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FILES = (
    ".gitignore",
    "AGENTS.md",
    "CLOUD-START.md",
    "DESIGN.md",
    "HANDOFF.md",
    "IMPLEMENTATION.md",
    "PLAN.md",
    "README.md",
    "scripts/check_artifacts.py",
    "scripts/package_handoff.py",
)


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts/check_artifacts.py")], check=True)
    for name in FILES:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(name)

    from labflow.development_paths import load_layout
    destination = load_layout().output('handoff/' + uuid4().hex)
    destination.mkdir(parents=True, exist_ok=False)
    archive_path = destination / "dgm-autolab-cloud-handoff.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, arcname=f"dgm-autolab/{name}")

    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC verification failed")
        expected = {f"dgm-autolab/{name}" for name in FILES}
        if set(archive.namelist()) != expected:
            raise RuntimeError("ZIP member list does not match the approved list")
        for name in FILES:
            if archive.read(f"dgm-autolab/{name}") != (ROOT / name).read_bytes():
                raise RuntimeError(f"ZIP content mismatch: {name}")

    digest = sha256(archive_path.read_bytes()).hexdigest()
    print(f"PASS: {len(FILES)} packaged files; CRC and byte comparison verified.")
    print(f"Archive: {archive_path}")
    print(f"Bytes: {archive_path.stat().st_size}")
    print(f"SHA256: {digest}")
    print("This packaging command does not upload files or create cloud environments.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
