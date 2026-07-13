from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ["app", "alembic", "tests", "scripts", "tools"]
OUTPUT_DIR = ROOT / "docs" / "line-by-line"
INDEX_PATH = OUTPUT_DIR / "INDEX.md"


@dataclass
class ContextBlock:
    start: int
    end: int
    kind: str
    name: str
    parent: str | None = None


def collect_source_files() -> list[Path]:
    files: list[Path] = []
    for source_dir in SOURCE_DIRS:
        files.extend(sorted((ROOT / source_dir).rglob("*.py")))
    return files


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def build_context_map(source: str) -> list[ContextBlock]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    blocks: list[ContextBlock] = []

    def visit(node: ast.AST, parent: str | None = None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                blocks.append(
                    ContextBlock(
                        start=child.lineno,
                        end=getattr(child, "end_lineno", child.lineno),
                        kind="class",
                        name=child.name,
                        parent=parent,
                    )
                )
                visit(child, child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                blocks.append(
                    ContextBlock(
                        start=child.lineno,
                        end=getattr(child, "end_lineno", child.lineno),
                        kind="function",
                        name=child.name,
                        parent=parent,
                    )
                )
                visit(child, child.name)
            else:
                visit(child, parent)

    visit(tree)
    return sorted(blocks, key=lambda item: (item.start, item.end))


def enclosing_block(blocks: list[ContextBlock], line_no: int) -> ContextBlock | None:
    candidates = [block for block in blocks if block.start <= line_no <= block.end]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.end - item.start, item.start))[0]


def indent_level(line: str) -> int:
    stripped = line.lstrip(" ")
    return (len(line) - len(stripped)) // 4


def humanize_name(name: str) -> str:
    chunks = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", name)
    if not chunks:
        return name
    return " ".join(chunk.lower() for chunk in chunks)


def assignment_target(line: str) -> str | None:
    if "=" not in line or "==" in line or ":=" in line:
        return None
    left = line.split("=", 1)[0].strip()
    if not left:
        return None
    return left


def explain_line(line: str, line_no: int, blocks: list[ContextBlock]) -> str:
    stripped = line.strip()
    block = enclosing_block(blocks, line_no)
    block_hint = ""
    if block:
        if block.kind == "class":
            block_hint = f" 이 줄은 `{block.name}` 클래스 정의 안에 있습니다."
        else:
            parent_text = f" `{block.parent}` 안의" if block.parent else ""
            block_hint = f" 이 줄은{parent_text} `{block.name}` 함수 안에 있습니다."

    if not stripped:
        return "빈 줄입니다. 코드를 기능별로 나눠 읽기 쉽게 만들기 위해 비워 둔 줄입니다."
    if stripped.startswith("#"):
        return f"주석입니다. 개발자가 의도나 설명을 글로 남긴 부분입니다.{block_hint}"
    if stripped.startswith("from ") or stripped.startswith("import "):
        return f"import 문입니다. 다른 파일이나 라이브러리의 기능을 현재 파일에서 사용할 수 있게 가져옵니다.{block_hint}"
    if stripped.startswith("@"):
        return f"데코레이터입니다. 바로 아래 함수나 클래스에 추가 동작이나 설정을 붙입니다.{block_hint}"
    if stripped.startswith("class "):
        name = stripped.split()[1].split("(")[0].rstrip(":")
        return f"`{name}` 클래스를 선언하는 줄입니다. 비슷한 데이터나 동작을 하나의 묶음으로 정의합니다."
    if stripped.startswith("def ") or stripped.startswith("async def "):
        name = stripped.split()[1].split("(")[0]
        prefix = "비동기 " if stripped.startswith("async def ") else ""
        return f"{prefix}함수 `{name}`를 선언하는 줄입니다. 이 아래에 `{humanize_name(name)}` 기능의 실제 동작을 작성합니다."
    if stripped.startswith("return "):
        return f"함수의 실행 결과를 호출한 쪽으로 돌려주는 줄입니다.{block_hint}"
    if stripped == "return":
        return f"함수를 즉시 끝내는 줄입니다. 특별한 값 없이 종료합니다.{block_hint}"
    if stripped.startswith("raise "):
        return f"예외를 발생시키는 줄입니다. 조건이 잘못됐을 때 실행을 멈추고 오류를 바깥으로 전달합니다.{block_hint}"
    if stripped.startswith("if "):
        return f"조건문 시작입니다. `if` 뒤 조건이 참일 때만 아래 들여쓴 코드가 실행됩니다.{block_hint}"
    if stripped.startswith("elif "):
        return f"앞의 `if`나 `elif`가 거짓일 때 추가 조건을 검사하는 줄입니다.{block_hint}"
    if stripped.startswith("else:"):
        return f"앞의 조건들이 모두 맞지 않을 때 실행할 기본 분기입니다.{block_hint}"
    if stripped.startswith("for "):
        return f"반복문 시작입니다. 리스트나 결과 집합의 각 값을 하나씩 꺼내 같은 작업을 반복합니다.{block_hint}"
    if stripped.startswith("while "):
        return f"조건이 참인 동안 같은 블록을 계속 반복하는 반복문입니다.{block_hint}"
    if stripped.startswith("with "):
        return f"리소스를 안전하게 열고 자동으로 정리하기 위한 문장입니다. 파일, 세션, 잠금 같은 자원 관리에 자주 씁니다.{block_hint}"
    if stripped.startswith("try:"):
        return f"오류가 날 수 있는 코드를 감싸는 시작점입니다. 뒤의 `except`와 함께 예외 처리를 합니다.{block_hint}"
    if stripped.startswith("except "):
        return f"`try` 블록에서 오류가 났을 때 그 오류를 받아 처리하는 줄입니다.{block_hint}"
    if stripped.startswith("finally:"):
        return f"오류 발생 여부와 관계없이 마지막에 반드시 실행할 정리 코드를 여는 줄입니다.{block_hint}"
    if stripped.startswith("yield "):
        return f"값을 하나씩 밖으로 내보내는 제너레이터 구문입니다. 전체를 한 번에 만들지 않고 순서대로 전달할 때 씁니다.{block_hint}"
    if stripped.startswith("pass"):
        return "아무 동작도 하지 않는 자리 표시자입니다. 현재 저장소에는 남기지 않는 것이 원칙이지만, 이 줄은 단순 문법 유지용 빈 블록일 가능성이 있습니다."
    if stripped.startswith("break"):
        return f"현재 반복문을 즉시 끝내는 줄입니다.{block_hint}"
    if stripped.startswith("continue"):
        return f"이번 반복만 건너뛰고 다음 반복으로 넘어가는 줄입니다.{block_hint}"
    if stripped.startswith(("op.", "context.", "batch_op.")):
        return f"Alembic 마이그레이션 또는 설정 API를 호출하는 줄입니다. 데이터베이스 구조를 바꾸거나 마이그레이션 컨텍스트를 조정합니다.{block_hint}"
    if ".relationship(" in stripped or stripped.startswith("relationship("):
        return f"SQLAlchemy relationship 설정입니다. 테이블 사이의 연결 관계를 객체 코드에서도 쉽게 따라갈 수 있게 합니다.{block_hint}"
    if "mapped_column(" in stripped:
        return f"ORM 컬럼 정의 줄입니다. 데이터베이스에 어떤 필드를 어떤 타입으로 저장할지 지정합니다.{block_hint}"
    if stripped.startswith("select(") or "select(" in stripped:
        return f"SQLAlchemy 조회 쿼리를 만드는 줄입니다. 데이터베이스에서 어떤 데이터를 읽을지 표현합니다.{block_hint}"
    if stripped.startswith("joinedload(") or "joinedload(" in stripped:
        return f"연관 데이터를 한 번에 미리 읽도록 설정하는 줄입니다. 나중에 추가 쿼리가 많이 발생하는 문제를 줄입니다.{block_hint}"
    if stripped.startswith("Field(") or "Field(" in stripped:
        return f"Pydantic 필드 검증 규칙을 지정하는 줄입니다. 길이 제한, 기본값, 최소/최대값 등을 설정합니다.{block_hint}"
    if stripped.startswith("BaseModel") or ": BaseModel" in stripped:
        return f"Pydantic 모델과 관련된 줄입니다. API 요청/응답 데이터를 검증하고 직렬화하기 위해 사용합니다.{block_hint}"
    target = assignment_target(stripped)
    if target:
        return f"`{target}`에 값을 저장하는 줄입니다. 앞에서 계산했거나 가져온 값을 나중에 다시 쓰기 위해 변수에 담습니다.{block_hint}"
    if stripped.endswith(":"):
        return f"새로운 코드 블록을 여는 줄입니다. 다음 줄부터 들여쓰기로 내부 동작을 구분합니다.{block_hint}"
    if "(" in stripped and stripped.endswith(")"):
        return f"함수나 메서드를 호출하는 줄입니다. 이미 만들어진 기능을 실행해서 결과를 얻거나 부수 효과를 발생시킵니다.{block_hint}"
    if stripped.startswith(("}", "]", ")")):
        return f"앞에서 열었던 자료구조나 함수 호출을 닫는 줄입니다.{block_hint}"
    if stripped.endswith((",", "{", "[", "(")):
        return f"여러 줄에 걸친 자료구조나 호출의 일부입니다. 이 줄은 전체 구조의 한 조각을 구성합니다.{block_hint}"
    return f"구현 세부 로직입니다. 위아래 코드와 함께 읽으면 데이터 준비, 조건 계산, 호출 조합 중 하나를 담당합니다.{block_hint}"


def render_markdown_for_file(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    blocks = build_context_map(source)
    parts = [
        f"# {rel(path)}",
        "",
        "초보자도 읽을 수 있도록 **한 줄씩 코드와 설명**을 나란히 정리한 문서입니다.",
        "",
        "| 줄 | 코드 | 설명 |",
        "|---:|---|---|",
    ]
    for idx, line in enumerate(lines, start=1):
        code = line.replace("|", "\\|").replace("\t", "    ")
        if code == "":
            code = "` `"
        else:
            code = f"`{code}`"
        explanation = explain_line(line, idx, blocks).replace("|", "\\|")
        parts.append(f"| {idx} | {code} | {explanation} |")
    return "\n".join(parts) + "\n"


def output_path_for(source_path: Path) -> Path:
    relative = source_path.relative_to(ROOT)
    return OUTPUT_DIR / relative.with_suffix(".md")


def generate() -> tuple[int, int]:
    files = collect_source_files()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    total_lines = 0
    index_lines = [
        "# 코드 한 줄 설명 인덱스",
        "",
        "이 디렉터리에는 저장소의 Python 코드에 대해 **한 줄씩 설명한 문서**가 들어 있습니다.",
        "",
    ]

    for source_path in files:
        content = render_markdown_for_file(source_path)
        destination = output_path_for(source_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        line_count = len(source_path.read_text(encoding="utf-8").splitlines())
        total_lines += line_count
        count += 1
        index_lines.append(f"- [{rel(source_path)}]({destination.relative_to(OUTPUT_DIR).as_posix()}) - {line_count} lines")

    INDEX_PATH.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return count, total_lines


if __name__ == "__main__":
    file_count, total_line_count = generate()
    print(f"generated files: {file_count}")
    print(f"generated lines: {total_line_count}")
    print(f"index: {INDEX_PATH}")
