from __future__ import annotations

import ast
import math
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "artifacts" / "smart_meal_backend_code_explanation.pptx"
SOURCE_DIRS = ["app", "alembic", "tests"]
LINES_PER_SLIDE = 24

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

DIR_SUMMARY = {
    "app/api/v1/endpoints": "FastAPI 엔드포인트 계층",
    "app/api": "API 의존성 및 라우터 계층",
    "app/core": "공통 설정, 보안, 예외, DB 연결 계층",
    "app/models": "SQLAlchemy ORM 모델 계층",
    "app/repositories": "DB 접근 캡슐화 계층",
    "app/schemas": "Pydantic 요청/응답 스키마 계층",
    "app/services": "비즈니스 로직 계층",
    "app/utils": "보조 유틸리티 계층",
    "alembic/versions": "DB 마이그레이션 버전 파일",
    "alembic": "Alembic 설정 파일",
    "tests": "테스트 시나리오 계층",
}

WORD_MAP = {
    "admin": "관리자",
    "analysis": "분석",
    "analyze": "분석",
    "analyses": "분석",
    "api": "API",
    "auth": "인증",
    "before": "식전",
    "after": "식후",
    "card": "카드",
    "cards": "카드",
    "common": "공통",
    "config": "설정",
    "consumption": "섭취",
    "create": "생성",
    "current": "현재",
    "dashboard": "대시보드",
    "database": "데이터베이스",
    "date": "날짜",
    "deactivate": "비활성화",
    "decode": "해석",
    "delete": "삭제",
    "dependencies": "의존성",
    "detail": "상세",
    "enums": "열거형",
    "exception": "예외",
    "exceptions": "예외",
    "file": "파일",
    "generate": "생성",
    "get": "조회",
    "hash": "해시",
    "health": "헬스체크",
    "history": "이력",
    "image": "이미지",
    "images": "이미지",
    "list": "목록",
    "login": "로그인",
    "logout": "로그아웃",
    "meal": "급식",
    "meals": "급식",
    "menu": "메뉴",
    "mock": "모의",
    "password": "비밀번호",
    "prepare": "준비",
    "profile": "프로필",
    "recommendation": "추천",
    "recommendations": "추천",
    "record": "기록",
    "records": "기록",
    "refresh": "재발급",
    "register": "등록",
    "repository": "리포지토리",
    "response": "응답",
    "result": "결과",
    "rfid": "RFID",
    "role": "권한",
    "router": "라우터",
    "save": "저장",
    "scan": "스캔",
    "schema": "스키마",
    "schemas": "스키마",
    "security": "보안",
    "service": "서비스",
    "services": "서비스",
    "serving": "배식",
    "signup": "회원가입",
    "summary": "요약",
    "test": "테스트",
    "tests": "테스트",
    "today": "오늘",
    "token": "토큰",
    "tokens": "토큰",
    "update": "수정",
    "upload": "업로드",
    "user": "사용자",
    "users": "사용자",
    "util": "유틸",
    "utils": "유틸",
    "validate": "검증",
    "verify": "검증",
    "vision": "비전",
}

ACTION_MAP = {
    "get": "조회",
    "list": "목록 조회",
    "create": "생성",
    "update": "수정",
    "delete": "삭제",
    "signup": "회원가입",
    "login": "로그인",
    "logout": "로그아웃",
    "refresh": "재발급",
    "change": "변경",
    "verify": "검증",
    "require": "권한 검사",
    "decode": "해석",
    "upload": "업로드",
    "deactivate": "비활성화",
    "scan": "스캔",
    "generate": "생성",
    "prepare": "준비",
    "bootstrap": "준비",
    "analyze": "분석",
    "reanalyze": "재분석",
    "save": "저장",
    "build": "구성",
    "ensure": "보장",
    "validate": "검증",
    "hash": "해시 생성",
    "assert": "검사",
}


@dataclass
class NodeSummary:
    start: int
    end: int
    text: str


@dataclass
class SlideContent:
    title: str
    subtitle: str
    code_lines: list[str]
    explanation_lines: list[str]


def collect_files() -> list[Path]:
    files: list[Path] = []
    for source_dir in SOURCE_DIRS:
        files.extend(sorted((ROOT / source_dir).rglob("*.py")))
    return files


def module_purpose(rel_path: str) -> str:
    for prefix, summary in sorted(DIR_SUMMARY.items(), key=lambda item: len(item[0]), reverse=True):
        if rel_path.startswith(prefix):
            return summary
    return "백엔드 구성 파일"


def translate_tokens(tokens: Iterable[str]) -> str:
    translated = []
    for token in tokens:
        translated.append(WORD_MAP.get(token.lower(), token))
    return " ".join(filter(None, translated))


def split_name(name: str) -> list[str]:
    parts = [part for part in re.split(r"[_\W]+", name) if part]
    expanded: list[str] = []
    for part in parts:
        expanded.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", part))
    return [item.lower() for item in expanded if item]


def summarize_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    route_desc = route_description(node)
    if route_desc:
        return route_desc
    tokens = split_name(node.name)
    if not tokens:
        return f"`{node.name}` 함수 정의"
    action = ACTION_MAP.get(tokens[0], "처리")
    target = translate_tokens(tokens[1:]) or "작업"
    return f"`{node.name}`: {target} {action} 로직"


def route_description(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            method = decorator.func.attr.upper()
            if method in {"GET", "POST", "PATCH", "DELETE", "PUT"}:
                path = "/"
                if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                    path = decorator.args[0].value or "/"
                return f"`{method} {path}` 엔드포인트를 처리하는 `{node.name}` 함수"
    return None


def summarize_class(node: ast.ClassDef, rel_path: str) -> str:
    if rel_path.startswith("app/models/"):
        return f"`class {node.name}`: DB 테이블/연관 관계를 표현하는 ORM 모델"
    if rel_path.startswith("app/schemas/"):
        return f"`class {node.name}`: 요청 또는 응답 검증용 Pydantic 스키마"
    if rel_path.startswith("tests/"):
        return f"`class {node.name}`: 테스트 보조 구조"
    return f"`class {node.name}` 정의"


def summarize_assign(node: ast.Assign, rel_path: str) -> str | None:
    targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
    if not targets:
        return None
    name = targets[0]
    if name in {"router", "api_router"}:
        return f"`{name}`: 라우터 객체를 만들고 엔드포인트를 묶는 설정"
    if name == "settings":
        return "`settings`: 환경 설정을 재사용하기 위한 전역 설정 인스턴스"
    if name in {"engine", "SessionLocal"}:
        return f"`{name}`: 데이터베이스 연결/세션 설정"
    if rel_path.startswith("tests/") and name.startswith("test_"):
        return f"`{name}`: 테스트용 데이터 또는 헬퍼"
    return None


def summarize_test_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    tokens = split_name(node.name)
    target = translate_tokens(tokens[1:]) or "시나리오"
    return f"`{node.name}`: {target} 동작을 검증하는 테스트"


def build_node_summaries(source: str, rel_path: str) -> list[NodeSummary]:
    if not source.strip():
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    summaries: list[NodeSummary] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            else:
                modules = [node.module or ""]
            summaries.append(
                NodeSummary(
                    start=node.lineno,
                    end=getattr(node, "end_lineno", node.lineno),
                    text=f"import 구문: {', '.join(filter(None, modules))} 의존성 로드",
                )
            )
        elif isinstance(node, ast.ClassDef):
            summaries.append(
                NodeSummary(
                    start=node.lineno,
                    end=getattr(node, "end_lineno", node.lineno),
                    text=summarize_class(node, rel_path),
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            text = summarize_test_function(node) if rel_path.startswith("tests/") and node.name.startswith("test_") else summarize_function(node)
            summaries.append(
                NodeSummary(
                    start=node.lineno,
                    end=getattr(node, "end_lineno", node.lineno),
                    text=text,
                )
            )
        elif isinstance(node, ast.Assign):
            text = summarize_assign(node, rel_path)
            if text:
                summaries.append(
                    NodeSummary(
                        start=node.lineno,
                        end=getattr(node, "end_lineno", node.lineno),
                        text=text,
                    )
                )
    return summaries


def build_chunk_explanations(rel_path: str, node_summaries: list[NodeSummary], start_line: int, end_line: int, part: int) -> list[str]:
    lines = []
    if part == 1:
        lines.append(f"파일 역할: {module_purpose(rel_path)}")

    overlaps = [
        summary.text
        for summary in node_summaries
        if not (summary.end < start_line or summary.start > end_line)
    ]
    seen: set[str] = set()
    for item in overlaps:
        if item not in seen:
            lines.append(item)
            seen.add(item)

    if not overlaps:
        lines.append(f"{start_line}~{end_line}행은 앞뒤 정의를 보조하는 구현 상세 또는 빈 줄/상수 영역")

    return lines[:10]


def line_numbered_chunk(lines: list[str], start_line: int, end_line: int) -> list[str]:
    width = len(str(end_line))
    result = []
    for index in range(start_line, end_line + 1):
        text = lines[index - 1].rstrip("\n")
        result.append(f"{index:>{width}}: {text}")
    return result


def build_slides(files: list[Path]) -> list[SlideContent]:
    slides: list[SlideContent] = []
    total_lines = 0
    for file_path in files:
        rel_path = file_path.relative_to(ROOT).as_posix()
        total_lines += sum(1 for _ in file_path.open("r", encoding="utf-8"))

    slides.append(
        SlideContent(
            title="스마트 급식 분석 시스템 백엔드 코드 설명",
            subtitle="전체 소스 코드 발표 자료",
            code_lines=[
                "포함 범위:",
                "  - app/**/*.py",
                "  - alembic/**/*.py",
                "  - tests/**/*.py",
                "",
                f"총 파일 수: {len(files)}",
                f"총 코드 라인 수: {total_lines}",
                "",
                "슬라이드 구성:",
                "  - 왼쪽: 실제 코드 원문",
                "  - 오른쪽: 코드 블록 설명",
            ],
            explanation_lines=[
                "이 자료는 백엔드 저장소의 Python 소스 파일 전체를 파일 단위로 분해해 설명합니다.",
                "긴 파일은 여러 장으로 나누어 코드 누락 없이 담았습니다.",
                "설명은 라우터, 서비스, 리포지토리, 모델, 스키마, 테스트 순으로 읽을 수 있게 자동 정리했습니다.",
            ],
        )
    )

    for file_path in files:
        rel_path = file_path.relative_to(ROOT).as_posix()
        source = file_path.read_text(encoding="utf-8")
        file_lines = source.splitlines()
        if not file_lines:
            file_lines = [""]
        node_summaries = build_node_summaries(source, rel_path)
        parts = math.ceil(len(file_lines) / LINES_PER_SLIDE)
        for part in range(parts):
            start_line = part * LINES_PER_SLIDE + 1
            end_line = min((part + 1) * LINES_PER_SLIDE, len(file_lines))
            slides.append(
                SlideContent(
                    title=rel_path,
                    subtitle=f"Part {part + 1}/{parts} | {start_line}-{end_line}행",
                    code_lines=line_numbered_chunk(file_lines, start_line, end_line),
                    explanation_lines=build_chunk_explanations(rel_path, node_summaries, start_line, end_line, part + 1),
                )
            )
    return slides


def make_paragraph(text: str, size: int, *, bold: bool = False, font: str = "Malgun Gothic", bullet: bool = False) -> str:
    bullet_attr = '<a:buChar char="•"/>' if bullet else '<a:buNone/>'
    bold_attr = ' b="1"' if bold else ""
    escaped = escape(text)
    return (
        "<a:p>"
        f"<a:pPr marL=\"171450\" indent=\"-171450\">{bullet_attr}</a:pPr>"
        f"<a:r><a:rPr lang=\"ko-KR\" sz=\"{size}\"{bold_attr}>"
        f"<a:latin typeface=\"{font}\"/><a:ea typeface=\"{font}\"/><a:cs typeface=\"{font}\"/>"
        f"</a:rPr><a:t xml:space=\"preserve\">{escaped}</a:t></a:r>"
        f"<a:endParaRPr lang=\"ko-KR\" sz=\"{size}\"><a:latin typeface=\"{font}\"/><a:ea typeface=\"{font}\"/><a:cs typeface=\"{font}\"/></a:endParaRPr>"
        "</a:p>"
    )


def make_text_box(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, paragraphs: list[str], *, fill: str, line: str) -> str:
    return f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="{escape(name)}"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
        <a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>
      </p:spPr>
      <p:txBody>
        <a:bodyPr wrap="square" lIns="91440" tIns="91440" rIns="91440" bIns="91440" anchor="t"/>
        <a:lstStyle/>
        {''.join(paragraphs)}
      </p:txBody>
    </p:sp>
    """


def render_slide(slide: SlideContent, slide_number: int) -> str:
    title_box = make_text_box(
        2,
        f"Title {slide_number}",
        274320,
        182880,
        11643360,
        731520,
        [
            make_paragraph(slide.title, 2200, bold=True),
            make_paragraph(slide.subtitle, 1100),
        ],
        fill="EAF2FF",
        line="9DBAF2",
    )

    code_paragraphs = [make_paragraph(line, 900, font="Courier New") for line in slide.code_lines]
    explanation_paragraphs = [make_paragraph(line, 1200, bullet=True) for line in slide.explanation_lines]

    code_box = make_text_box(
        3,
        f"Code {slide_number}",
        274320,
        1097280,
        6675120,
        5486400,
        code_paragraphs,
        fill="F8F8F8",
        line="C7C7C7",
    )
    explanation_box = make_text_box(
        4,
        f"Explanation {slide_number}",
        7223760,
        1097280,
        4443480,
        5486400,
        explanation_paragraphs,
        fill="FFF8E7",
        line="E5C66D",
    )

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {title_box}
      {code_box}
      {explanation_box}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def slide_rel() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{R_NS}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""


def render_content_types(slide_count: int) -> str:
    slide_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>
  <Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>
  <Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
{slide_overrides}
</Types>
"""


def render_root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def render_app_props(slide_count: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>OpenAI Codex</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>{slide_count}</Slides>
  <Notes>0</Notes>
  <HiddenSlides>0</HiddenSlides>
  <MMClips>0</MMClips>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Slides</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>{slide_count}</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="{slide_count}" baseType="lpstr">
      {''.join('<vt:lpstr>Slide</vt:lpstr>' for _ in range(slide_count))}
    </vt:vector>
  </TitlesOfParts>
  <Company>OpenAI</Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>1.0</AppVersion>
</Properties>
"""


def render_core_props() -> str:
    created = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Smart Meal Backend Code Explanation</dc:title>
  <dc:creator>OpenAI Codex</dc:creator>
  <cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>
"""


def render_presentation(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'    <p:sldId id="{256 + index}" r:id="rId{5 + index}"/>'
        for index in range(slide_count)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
{slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle/>
</p:presentation>
"""


def render_presentation_rels(slide_count: int) -> str:
    slide_rels = "\n".join(
        f'  <Relationship Id="rId{5 + index}" Type="{R_NS}/slide" Target="slides/slide{index + 1}.xml"/>'
        for index in range(slide_count)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{R_NS}/slideMaster" Target="slideMasters/slideMaster1.xml"/>
  <Relationship Id="rId2" Type="{R_NS}/presProps" Target="presProps.xml"/>
  <Relationship Id="rId3" Type="{R_NS}/viewProps" Target="viewProps.xml"/>
  <Relationship Id="rId4" Type="{R_NS}/tableStyles" Target="tableStyles.xml"/>
{slide_rels}
</Relationships>
"""


def render_pres_props() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentationPr xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">
  <p:showPr loop="0" useTimings="0"/>
</p:presentationPr>
"""


def render_view_props() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:viewPr xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}" lastView="sldView">
  <p:normalViewPr>
    <p:restoredLeft sz="15620"/>
    <p:restoredTop sz="94660"/>
  </p:normalViewPr>
  <p:slideViewPr/>
  <p:outlineViewPr/>
  <p:notesTextViewPr/>
  <p:gridSpacing cx="78028800" cy="78028800"/>
</p:viewPr>
"""


def render_table_styles() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:tblStyleLst xmlns:a="{A_NS}" def="TableStyleMedium2"/>
"""


def render_slide_master() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">
  <p:cSld name="Office Theme">
    <p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="2147483649" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle/>
    <p:bodyStyle/>
    <p:otherStyle/>
  </p:txStyles>
</p:sldMaster>
"""


def render_slide_master_rels() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{R_NS}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="{R_NS}/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""


def render_slide_layout() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}" type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""


def render_theme() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{A_NS}" name="CodexTheme">
  <a:themeElements>
    <a:clrScheme name="Codex">
      <a:dk1><a:srgbClr val="1F1F1F"/></a:dk1>
      <a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="273043"/></a:dk2>
      <a:lt2><a:srgbClr val="F4F7FB"/></a:lt2>
      <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
      <a:accent2><a:srgbClr val="C0504D"/></a:accent2>
      <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
      <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
      <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
      <a:accent6><a:srgbClr val="F79646"/></a:accent6>
      <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
      <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Codex Fonts">
      <a:majorFont>
        <a:latin typeface="Malgun Gothic"/>
        <a:ea typeface="Malgun Gothic"/>
        <a:cs typeface="Malgun Gothic"/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface="Malgun Gothic"/>
        <a:ea typeface="Malgun Gothic"/>
        <a:cs typeface="Malgun Gothic"/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Codex Format">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt2"/></a:solidFill>
        <a:solidFill><a:schemeClr val="accent1"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="dk1"/></a:solidFill></a:ln>
        <a:ln w="25400"><a:solidFill><a:schemeClr val="dk1"/></a:solidFill></a:ln>
        <a:ln w="38100"><a:solidFill><a:schemeClr val="dk1"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt2"/></a:solidFill>
        <a:solidFill><a:schemeClr val="accent1"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>
"""


def write_pptx(slides: list[SlideContent]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        slide_count = len(slides)
        zf.writestr("[Content_Types].xml", render_content_types(slide_count))
        zf.writestr("_rels/.rels", render_root_rels())
        zf.writestr("docProps/app.xml", render_app_props(slide_count))
        zf.writestr("docProps/core.xml", render_core_props())
        zf.writestr("ppt/presentation.xml", render_presentation(slide_count))
        zf.writestr("ppt/_rels/presentation.xml.rels", render_presentation_rels(slide_count))
        zf.writestr("ppt/presProps.xml", render_pres_props())
        zf.writestr("ppt/viewProps.xml", render_view_props())
        zf.writestr("ppt/tableStyles.xml", render_table_styles())
        zf.writestr("ppt/slideMasters/slideMaster1.xml", render_slide_master())
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", render_slide_master_rels())
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", render_slide_layout())
        zf.writestr("ppt/theme/theme1.xml", render_theme())
        for index, slide in enumerate(slides, start=1):
            zf.writestr(f"ppt/slides/slide{index}.xml", render_slide(slide, index))
            zf.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", slide_rel())


def main() -> None:
    files = collect_files()
    slides = build_slides(files)
    write_pptx(slides)
    print(f"generated: {OUTPUT_PATH}")
    print(f"slides: {len(slides)}")


if __name__ == "__main__":
    main()
