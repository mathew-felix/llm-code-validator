from __future__ import annotations

import argparse
import json
import sys
import tomllib

from .core import CheckResult, check_paths, check_stdin, staged_python_files
from .fixes import fix_file
from .formatting import format_github, format_json, format_text
from .signatures import validate_signature_database
from .versioning import build_version_context


def check_staged(requirements: str | None = None, python_version: str | None = None) -> CheckResult:
    files = staged_python_files()
    return check_paths(files, requirements=requirements, python_version=python_version) if files else check_paths([])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-code-validator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check Python files for known API drift.")
    check.add_argument("paths", nargs="*", help="Files or directories to scan. Use '-' for stdin.")
    check.add_argument("--staged", action="store_true", help="Check staged Python files from git.")
    check.add_argument("--format", choices=["text", "json", "github"], default="text")
    check.add_argument("--requirements", help="Requirements file used for version assumptions.")
    check.add_argument("--python-version", help="Target Python version label for result context.")
    check.add_argument("--show-low-confidence", action="store_true", help="Show lower-confidence diagnostics.")

    fix = subparsers.add_parser("fix", help="Preview or apply deterministic safe fixes.")
    fix.add_argument("paths", nargs="+", help="Python files to fix.")
    fix.add_argument("--write", action="store_true", help="Write safe fixes to disk.")
    fix.add_argument("--requirements", help="Requirements file used for version assumptions.")
    fix.add_argument("--python-version", help="Target Python version label for result context.")

    validate = subparsers.add_parser("validate-signatures", help="Validate the signature database.")
    validate.add_argument("--path", help="Path to library_signatures.json.")
    validate.add_argument(
        "--require-official-evidence",
        action="store_true",
        help="Require diagnostic rules to use source_url or release_note instead of generic notes.",
    )
    return parser


def _render(result: CheckResult, output_format: str) -> str:
    if output_format == "json":
        return format_json(result)
    if output_format == "github":
        return format_github(result)
    return format_text(result)


def _print_error(message: str) -> None:
    print(f"llm-code-validator: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            if args.staged:
                result = check_paths(
                    staged_python_files(),
                    requirements=args.requirements,
                    python_version=args.python_version,
                    show_low_confidence=args.show_low_confidence,
                )
            elif args.paths == ["-"]:
                result = check_stdin(args.requirements, args.python_version, args.show_low_confidence)
            elif args.paths:
                result = check_paths(args.paths, args.requirements, args.python_version, args.show_low_confidence)
            else:
                parser.error("check requires a path, '-', or --staged")
            output = _render(result, args.format)
            if output:
                print(output)
            return 1 if result.diagnostics else 0
        if args.command == "fix":
            version_context = build_version_context(args.paths, args.requirements, args.python_version)
            exit_code = 0
            for path in args.paths:
                result = fix_file(path, write=args.write, version_context=version_context)
                for preview in result.previews:
                    print(preview)
                for skipped in result.skipped:
                    print(skipped)
                if result.skipped:
                    exit_code = 1
            return exit_code
        if args.command == "validate-signatures":
            errors = validate_signature_database(args.path, args.require_official_evidence)
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            print("OK: signature database is valid")
            return 0
    except FileNotFoundError as exc:
        _print_error(f"file not found: {exc.filename}")
        return 2
    except PermissionError as exc:
        _print_error(f"permission denied: {exc.filename}")
        return 2
    except json.JSONDecodeError as exc:
        _print_error(f"invalid JSON: {exc.msg}")
        return 2
    except tomllib.TOMLDecodeError as exc:
        _print_error(f"invalid TOML: {exc}")
        return 2
    except RuntimeError as exc:
        _print_error(str(exc))
        return 2
    except Exception as exc:
        _print_error(f"unexpected {type(exc).__name__}: {exc}")
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
