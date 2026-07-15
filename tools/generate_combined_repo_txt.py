from __future__ import annotations

from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT_DIR / "artifacts" / "backend_combined_source_bundle.txt"

INCLUDE_FILES = {
    ".dockerignore",
    ".env.example",
    ".gitignore",
    ".python-version",
    "Dockerfile",
    "README.md",
    "alembic.ini",
    "pytest.ini",
    "requirements.txt",
    "start.sh",
    "vercel.json",
}
INCLUDE_SUFFIXES = {".py", ".md"}
EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "artifacts",
    "uploads",
}


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT_DIR)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    return path.name in INCLUDE_FILES or path.suffix.lower() in INCLUDE_SUFFIXES


def collect_files() -> list[Path]:
    return sorted(
        (path for path in ROOT_DIR.rglob("*") if path.is_file() and should_include(path)),
        key=lambda path: path.relative_to(ROOT_DIR).as_posix(),
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def generate_txt() -> tuple[Path, int]:
    files = collect_files()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    sections = [
        "BACKEND COMBINED SOURCE BUNDLE",
        f"Generated at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Included files: {len(files)}",
        "Secrets and generated/uploaded files are excluded.",
        "",
    ]
    for path in files:
        relative = path.relative_to(ROOT_DIR).as_posix()
        content = read_text(path)
        numbered = "\n".join(
            f"{line_number:04d}: {line}"
            for line_number, line in enumerate(content.splitlines(), start=1)
        )
        sections.extend(
            [
                "=" * 100,
                f"FILE: {relative}",
                "=" * 100,
                numbered,
                "",
            ]
        )

    OUTPUT_PATH.write_text("\n".join(sections), encoding="utf-8")
    return OUTPUT_PATH, len(files)


if __name__ == "__main__":
    output_path, file_count = generate_txt()
    print(f"generated: {output_path}")
    print(f"included files: {file_count}")
