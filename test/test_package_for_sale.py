import zipfile
from pathlib import Path

from scripts.package_for_sale import _should_include, build_package


def test_should_include_excludes_env_file():
    assert _should_include(Path(".env")) is False


def test_should_include_excludes_pycache():
    assert _should_include(Path("src/modules/__pycache__/triage.cpython-312.pyc")) is False


def test_should_include_excludes_git_dir():
    assert _should_include(Path(".git/config")) is False


def test_should_include_excludes_venv():
    assert _should_include(Path(".venv/Lib/site-packages/foo.py")) is False


def test_should_include_excludes_build_caches():
    assert _should_include(Path(".mypy_cache/3.12/cache.0.db")) is False
    assert _should_include(Path(".ruff_cache/0/index")) is False
    assert _should_include(Path(".pytest_cache/CACHEDIR.TAG")) is False


def test_should_include_excludes_generated_exports():
    assert _should_include(Path("factures/dupont.xlsx")) is False


def test_should_include_keeps_real_project_files():
    assert _should_include(Path("src/modules/triage.py")) is True
    assert _should_include(Path("README.md")) is True
    assert _should_include(Path(".env.example")) is True


def test_build_package_creates_zip_without_secrets(tmp_path):
    archive_path, count = build_package(output_dir=tmp_path)

    assert archive_path.exists()
    assert count > 0

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()

    assert ".env" not in names
    assert ".env.example" in names
    assert "README.md" in names
    assert "app.py" in names
    assert not any(name.startswith(".git/") for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(".venv" in name for name in names)
    assert not any(".mypy_cache" in name for name in names)
    assert not any(".ruff_cache" in name for name in names)
    assert not any(".pytest_cache" in name for name in names)
