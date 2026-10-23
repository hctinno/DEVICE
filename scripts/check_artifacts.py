"""Check planning-document integrity; does not validate laboratory operation."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("README.md", "PLAN.md", "IMPLEMENTATION.md", "DESIGN.md", "AGENTS.md", "HANDOFF.md", "CLOUD-START.md")
BAD_TOKENS = ("???", "\ufffd", "\u6fe1", "\u6e72", "\u907a", "\u5a9b", "\uf9e1")
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    errors: list[str] = []
    files = sorted(ROOT.glob("*.md"))
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"Missing document: {name}")

    link_count = 0
    for path in files:
        try:
            content = path.read_bytes().decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            errors.append(f"Invalid UTF-8: {path.name}: {exc}")
            continue
        if not content.strip():
            errors.append(f"Empty document: {path.name}")
        for token in BAD_TOKENS:
            if token in content:
                errors.append(f"Encoding marker in {path.name}: {ascii(token)}")
        for raw_target in LINK_PATTERN.findall(content):
            target = raw_target.strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0])
            if not relative:
                continue
            link_count += 1
            if not (path.parent / relative).is_file():
                errors.append(f"Broken local link in {path.name}: {target}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {len(files)} UTF-8 documents; {link_count} local links; no encoding markers.")
    print("Scope: document integrity only. No hardware, AI workflow, or conformity validation performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
