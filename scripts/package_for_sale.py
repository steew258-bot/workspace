"""Genere une archive zip du template pret a distribuer (ex: upload Gumroad).

Usage:
    python scripts/package_for_sale.py

Exclut tout ce qui ne doit jamais partir dans le zip vendu : secrets reels
(.env), historique git, environnements virtuels, caches. Inclut .env.example
(le template a completer par l'acheteur), jamais .env.
"""

import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"

EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".ruff_cache",
    ".pytest_cache",
    ".claude",
    "dist",
}

EXCLUDE_FILE_NAMES = {".env"}
EXCLUDE_SUFFIXES = {".pyc"}


def _should_include(relative_path: Path) -> bool:
    if relative_path.name in EXCLUDE_FILE_NAMES:
        return False
    if relative_path.suffix in EXCLUDE_SUFFIXES:
        return False
    if set(relative_path.parts) & EXCLUDE_DIR_NAMES:
        return False
    return True


def build_package(output_dir: Path = DIST_DIR) -> tuple[Path, int]:
    output_dir.mkdir(exist_ok=True)
    archive_name = f"ops-agent-{date.today().isoformat()}.zip"
    archive_path = output_dir / archive_name

    included = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir():
                continue
            relative_path = path.relative_to(ROOT)
            if not _should_include(relative_path):
                continue
            zf.write(path, arcname=str(relative_path))
            included += 1

    return archive_path, included


if __name__ == "__main__":
    result_path, file_count = build_package()
    size_kb = result_path.stat().st_size / 1024
    print(f"Package cree : {result_path} ({file_count} fichiers, {size_kb:.0f} Ko)")
