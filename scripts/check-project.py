#!/usr/bin/env python3
"""Lightweight repository consistency checks for Linsae."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "README.md",
    "docs/architecture.md",
    "docs/development-roadmap.md",
    "docs/device-research.md",
    "manifest/README.md",
    "device/xiaomi/earth/README.md",
    ".github/workflows/validate.yml",
)


def main() -> int:
    missing = [item for item in REQUIRED if not (ROOT / item).is_file()]
    if missing:
        print("Missing required project files:")
        for item in missing:
            print(f"  - {item}")
        return 1

    # Validate XML files when present. No placeholder XML manifests are generated.
    xml_files = sorted(ROOT.rglob("*.xml"))
    for path in xml_files:
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            print(f"Invalid XML: {path.relative_to(ROOT)}: {exc}")
            return 1

    print(f"Project checks passed; validated {len(REQUIRED)} required files.")
    print(f"Parsed {len(xml_files)} XML file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
