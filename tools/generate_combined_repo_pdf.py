from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT_DIR / "artifacts" / "backend_combined_source_bundle.pdf"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf")
FONT_NAME = "NotoSansGothic"

INCLUDE_FILES = {
    ".env.example",
    ".gitignore",
    "README.md",
    "alembic.ini",
    "requirements.txt",
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
    "docs/line-by-line",
}


def register_fonts() -> None:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Font file not found: {FONT_PATH}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT_DIR)
    relative_text = relative.as_posix()
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if any(relative_text.startswith(prefix) for prefix in EXCLUDED_PARTS if "/" in prefix):
        return False
    return path.name in INCLUDE_FILES or path.suffix in INCLUDE_SUFFIXES


def collect_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT_DIR.rglob("*"):
        if not path.is_file():
            continue
        if should_include(path):
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT_DIR).as_posix())


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="KTitle",
            parent=styles["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KHeading",
            parent=styles["Heading2"],
            fontName=FONT_NAME,
            fontSize=13,
            leading=18,
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KBody",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KCode",
            fontName="Courier",
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    return styles


def with_line_numbers(text: str) -> str:
    lines = text.splitlines() or [""]
    return "\n".join(f"{index:04d}: {line}" for index, line in enumerate(lines, start=1))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def build_story(files: list[Path]):
    styles = build_styles()
    story = []

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("Backend Combined Source Bundle", styles["KTitle"]))
    story.append(
        Paragraph(
            "방금 생성한 설명 폴더(<b>docs/line-by-line</b>)를 제외한 저장소의 코드와 주요 문서를 하나의 PDF로 묶은 파일입니다.",
            styles["KBody"],
        )
    )
    story.append(Paragraph(f"생성 시각: {generated_at}", styles["KBody"]))
    story.append(Paragraph(f"포함 파일 수: {len(files)}", styles["KBody"]))
    story.append(Spacer(1, 8 * mm))

    index_rows = [["No.", "File Path"]]
    for index, path in enumerate(files, start=1):
        index_rows.append([str(index), path.relative_to(ROOT_DIR).as_posix()])

    index_table = Table(index_rows, colWidths=[15 * mm, 160 * mm], repeatRows=1)
    index_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(index_table)
    story.append(PageBreak())

    for index, path in enumerate(files, start=1):
        relative_path = path.relative_to(ROOT_DIR).as_posix()
        story.append(Paragraph(f"{index}. {escape(relative_path)}", styles["KHeading"]))
        content = with_line_numbers(read_text(path))
        story.append(Preformatted(content, styles["KCode"], dedent=0))
        if index != len(files):
            story.append(PageBreak())

    return story


def generate_pdf() -> Path:
    register_fonts()
    files = collect_files()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Backend Combined Source Bundle",
        author="OpenAI Codex",
    )
    doc.build(build_story(files))
    return OUTPUT_PATH


if __name__ == "__main__":
    output_path = generate_pdf()
    print(output_path)
