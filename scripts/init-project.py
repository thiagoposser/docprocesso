#!/usr/bin/env python3
"""Initialize a copy of this template without third-party dependencies.

The replacement map is deliberately centralized so future fields (application
name, Django package, Angular title and environment values) can be added safely.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_FILES = [
    ROOT / "frontend" / "package.json",
    ROOT / "frontend" / "angular.json",
    ROOT / "frontend" / "src" / "index.html",
    ROOT / "docker" / "frontend" / "Dockerfile",
    ROOT / "README.md",
]


def slug(value: str) -> str:
    result = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return "-".join(filter(None, result.split("-")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Personaliza uma cópia do template.")
    parser.add_argument("project_name", help="Nome legível do novo projeto")
    parser.add_argument("--dry-run", action="store_true", help="Mostra as alterações sem gravar")
    args = parser.parse_args()
    replacements = {"Base Angular + Django": args.project_name, "base-frontend": f"{slug(args.project_name)}-frontend"}

    for path in TEXT_FILES:
        content = path.read_text(encoding="utf-8")
        updated = content
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != content:
            print(f"{'Alteraria' if args.dry_run else 'Atualizando'}: {path.relative_to(ROOT)}")
            if not args.dry_run:
                path.write_text(updated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
