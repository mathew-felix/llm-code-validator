from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REQUIREMENTS_FILENAMES = ("requirements.txt", "pyproject.toml", "poetry.lock", "uv.lock", "Pipfile.lock")
_REQ_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*([<>=!~]=?|===)?\s*([^\s;#]+)?")
_LOCK_NAME_PATTERN = re.compile(r'^\s*name\s*=\s*["\']([^"\']+)["\']')
_LOCK_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']')


@dataclass(frozen=True)
class VersionContext:
    requirements_path: str | None
    dependencies: dict[str, str]
    python_version: str | None = None
    used_defaults: bool = False

    def assumption_for(self, library: str, fallback: str) -> str:
        pinned = self.dependencies.get(library.lower())
        if pinned:
            return f"{library}{pinned}"
        return fallback


def parse_requirements(path: str | Path) -> dict[str, str]:
    requirements_path = Path(path)
    dependencies: dict[str, str] = {}
    for raw_line in _read_text_lenient(requirements_path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = _REQ_PATTERN.match(line)
        if not match:
            continue
        name, operator, version = match.groups()
        normalized = name.replace("_", "-").lower()
        dependencies[normalized] = f"{operator or ''}{version or ''}"
    return dependencies


def _read_text_lenient(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="ignore")


def _normalize_name(name: str) -> str:
    return name.replace("_", "-").lower()


def _parse_requirement_string(requirement: str) -> tuple[str, str] | None:
    match = _REQ_PATTERN.match(requirement)
    if not match:
        return None
    name, operator, version = match.groups()
    return _normalize_name(name), f"{operator or ''}{version or ''}"


def parse_pyproject(path: str | Path) -> dict[str, str]:
    data = tomllib.loads(_read_text_lenient(Path(path)))
    dependencies: dict[str, str] = {}
    project = data.get("project", {})
    for requirement in project.get("dependencies", []) or []:
        parsed = _parse_requirement_string(requirement)
        if parsed:
            dependencies[parsed[0]] = parsed[1]
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for name, value in poetry_deps.items():
        if name.lower() == "python":
            continue
        if isinstance(value, str):
            dependencies[_normalize_name(name)] = value
        elif isinstance(value, dict):
            dependencies[_normalize_name(name)] = str(value.get("version", ""))
    return dependencies


def parse_toml_lock(path: str | Path) -> dict[str, str]:
    dependencies: dict[str, str] = {}
    data = tomllib.loads(_read_text_lenient(Path(path)))
    packages = data.get("package", [])
    if isinstance(packages, dict):
        packages = list(packages.values())
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = package.get("name")
        version = package.get("version")
        if name and version:
            dependencies[_normalize_name(str(name))] = f"=={version}"
    return dependencies


def parse_pipfile_lock(path: str | Path) -> dict[str, str]:
    import json

    data = json.loads(_read_text_lenient(Path(path)))
    dependencies: dict[str, str] = {}
    for section in ("default", "develop"):
        for name, value in data.get(section, {}).items():
            if isinstance(value, str):
                dependencies[_normalize_name(name)] = value
            elif isinstance(value, dict):
                dependencies[_normalize_name(name)] = str(value.get("version", ""))
    return dependencies


def parse_dependency_file(path: str | Path) -> dict[str, str]:
    dep_path = Path(path)
    if dep_path.name == "requirements.txt":
        return parse_requirements(dep_path)
    if dep_path.name == "pyproject.toml":
        return parse_pyproject(dep_path)
    if dep_path.name in {"poetry.lock", "uv.lock"}:
        return parse_toml_lock(dep_path)
    if dep_path.name == "Pipfile.lock":
        return parse_pipfile_lock(dep_path)
    return parse_requirements(dep_path)


def discover_requirements(start: str | Path = ".") -> Path | None:
    root = Path(start)
    if root.is_file():
        root = root.parent
    for filename in DEFAULT_REQUIREMENTS_FILENAMES:
        candidate = root / filename
        if candidate.exists():
            return candidate
    return None


def build_version_context(
    paths: list[str] | None = None,
    requirements: str | None = None,
    python_version: str | None = None,
) -> VersionContext:
    if requirements:
        req_path = Path(requirements)
        return VersionContext(str(req_path), parse_dependency_file(req_path), python_version, used_defaults=False)

    search_root = "."
    if paths:
        first_path = Path(paths[0])
        search_root = str(first_path.parent if first_path.is_file() else first_path)
    discovered = discover_requirements(search_root)
    if discovered:
        return VersionContext(str(discovered), parse_dependency_file(discovered), python_version, used_defaults=False)
    return VersionContext(None, {}, python_version, used_defaults=True)
