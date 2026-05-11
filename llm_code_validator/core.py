from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from .diagnostics import CheckResult, Diagnostic, Fix
from .signatures import SignatureRule, find_rule, load_signatures
from .versioning import VersionContext, build_version_context


STDIN_PATH = "<stdin>"
EXCLUDED_DIR_NAMES = {
    ".eggs",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
}
EXCLUDED_DIR_PARTS = {"Lib", "site-packages"}


class _CallExtractor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.aliases: dict[str, str] = {}
        self.alias_confidence: dict[str, float] = {}
        self.calls: list[tuple[str, str, int, int, float, set[str]]] = []
        self.dynamic_imports: list[tuple[str, int, int]] = []
        self.returns: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            library = alias.name.split(".")[0]
            used_name = alias.asname or alias.name
            self.aliases[used_name] = library
            self.alias_confidence[used_name] = 1.0
            self.calls.append((library, alias.name, node.lineno, node.col_offset, 1.0, set()))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            return
        module = node.module or ""
        library = module.split(".")[0]
        for alias in node.names:
            used_name = alias.asname or alias.name
            self.aliases[used_name] = library
            self.alias_confidence[used_name] = 1.0
            qualified_name = f"{module}.{alias.name}" if module else alias.name
            self.calls.append((library, qualified_name, node.lineno, node.col_offset, 1.0, set()))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                root = _root_name(child.value) if child.value else None
                if root in self.aliases:
                    self.returns[node.name] = self.aliases[root]
                    break
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
            value = node.value.func if isinstance(node.value, ast.Call) else node.value
            root = _root_name(value)
            if root in self.aliases:
                self.aliases[target] = self.aliases[root]
                self.alias_confidence[target] = self.alias_confidence.get(root, 0.85)
            elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                function_name = node.value.func.id
                if function_name in self.returns:
                    self.aliases[target] = self.returns[function_name]
                    self.alias_confidence[target] = 0.75
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        root = _root_name(node)
        if root in self.aliases:
            symbol = _attribute_name(node)
            if "." in symbol:
                _, tail = symbol.split(".", 1)
                symbol = f"{self.aliases[root]}.{tail}"
            self.calls.append(
                (
                    self.aliases[root],
                    symbol,
                    node.lineno,
                    node.col_offset,
                    self.alias_confidence.get(root, 0.75),
                    set(),
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            library = _first_string_arg(node)
            if library:
                self.dynamic_imports.append((library.split(".")[0], node.lineno, node.col_offset))
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
        ):
            library = _first_string_arg(node)
            if library:
                self.dynamic_imports.append((library.split(".")[0], node.lineno, node.col_offset))
        root = _root_name(node.func)
        if root in self.aliases:
            symbol = _call_symbol(node.func, self.aliases[root])
            if symbol:
                keywords = {keyword.arg for keyword in node.keywords if keyword.arg}
                self.calls.append(
                    (
                        self.aliases[root],
                        symbol,
                        node.lineno,
                        node.col_offset,
                        self.alias_confidence.get(root, 0.75),
                        keywords,
                    )
                )
        self.generic_visit(node)


def _root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Call):
        return _root_name(current.func)
    if isinstance(current, ast.Name):
        return current.id
    return None


def _attribute_name(node: ast.Attribute) -> str:
    parts = [node.attr]
    current = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _call_symbol(node: ast.AST, library: str) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        symbol = _attribute_name(node)
        if "." in symbol:
            _, tail = symbol.split(".", 1)
            return f"{library}.{tail}"
        return symbol
    return None


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _diagnostic(
    path: str,
    line: int,
    column: int,
    library: str,
    rule: SignatureRule,
    version_context: VersionContext,
    confidence: float = 1.0,
) -> Diagnostic:
    assumption = version_context.assumption_for(library, rule.version_assumption)
    return Diagnostic(
        path=path,
        line=line,
        column=column + 1,
        code="LCV001",
        severity=rule.severity,
        library=library,
        symbol=rule.symbol,
        message=rule.message,
        evidence=rule.evidence,
        replacement=rule.replacement,
        confidence=confidence,
        version_assumption=assumption,
        fix=Fix(replacement=rule.replacement, safety=rule.fix_safety),
    )


def check_source(
    source: str,
    path: str | None = None,
    version_context: VersionContext | None = None,
    show_low_confidence: bool = False,
) -> CheckResult:
    display_path = path or STDIN_PATH
    version_context = version_context or VersionContext(None, {}, used_defaults=True)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        diagnostic = Diagnostic(
            path=display_path,
            line=exc.lineno or 1,
            column=exc.offset or 1,
            code="LCV900",
            severity="error",
            library="python",
            symbol="syntax",
            message=f"Python syntax error: {exc.msg}",
            confidence=1.0,
        )
        return CheckResult(checked_files=1, diagnostics=[diagnostic])

    extractor = _CallExtractor()
    extractor.visit(tree)
    signatures = load_signatures()
    diagnostics: list[Diagnostic] = []
    seen: set[tuple[str, int, str]] = set()

    for library, symbol, line, column, confidence, keywords in extractor.calls:
        rule = find_rule(library, symbol, signatures, keywords)
        if not rule:
            continue
        if confidence < 0.8 and not show_low_confidence:
            continue
        key = (library, line, rule.symbol)
        if key in seen:
            continue
        seen.add(key)
        diagnostics.append(_diagnostic(display_path, line, column, library, rule, version_context, confidence))

    for library, line, column in extractor.dynamic_imports:
        diagnostics.append(
            Diagnostic(
                path=display_path,
                line=line,
                column=column + 1,
                code="LCV910",
                severity="warning",
                library=library,
                symbol="dynamic-import",
                message=f"Dynamic import of {library!r} may hide API usage from static checks.",
                confidence=0.6,
            )
        )

    warnings = []
    if version_context.used_defaults:
        warnings.append("No requirements file was evaluated; diagnostics use default signature version assumptions.")
    return CheckResult(
        checked_files=1,
        diagnostics=diagnostics,
        warnings=warnings,
    )


def check_file(
    path: str | Path,
    version_context: VersionContext | None = None,
    show_low_confidence: bool = False,
) -> CheckResult:
    file_path = Path(path)
    try:
        source = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        diagnostic = Diagnostic(
            path=str(file_path),
            line=1,
            column=1,
            code="LCV901",
            severity="error",
            library="filesystem",
            symbol="read",
            message=f"Could not read file: {exc}",
            confidence=1.0,
        )
        return CheckResult(checked_files=0, diagnostics=[diagnostic])
    return check_source(source, str(file_path), version_context, show_low_confidence)


def iter_python_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.py") if p.is_file() and not _is_excluded_python_path(p)))
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return files


def _is_excluded_python_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts.intersection(EXCLUDED_DIR_NAMES):
        return True
    return EXCLUDED_DIR_PARTS.issubset(parts)


def merge_results(results: list[CheckResult]) -> CheckResult:
    return CheckResult(
        checked_files=sum(result.checked_files for result in results),
        diagnostics=[diagnostic for result in results for diagnostic in result.diagnostics],
        warnings=sorted({warning for result in results for warning in result.warnings}),
    )


def check_paths(
    paths: list[str],
    requirements: str | None = None,
    python_version: str | None = None,
    show_low_confidence: bool = False,
) -> CheckResult:
    files = iter_python_files(paths)
    if not files:
        return CheckResult(checked_files=0, warnings=["No Python files were found."])
    version_context = build_version_context(paths, requirements, python_version)
    return merge_results([check_file(path, version_context, show_low_confidence) for path in files])


def staged_python_files() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "--", "*.py"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Could not read staged files from git.")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def check_stdin(
    requirements: str | None = None,
    python_version: str | None = None,
    show_low_confidence: bool = False,
) -> CheckResult:
    version_context = build_version_context(None, requirements, python_version)
    return check_source(sys.stdin.read(), STDIN_PATH, version_context, show_low_confidence)
