from __future__ import annotations

import argparse
import json
import sys
import tomllib

from .ai_review import (
    ProviderConfig,
    build_ai_payload,
    default_key_env,
    render_ai_payload,
    validate_ai_provider,
    write_ai_audit_log,
)
from .config import load_config, validate_provider_allowed
from .core import CheckResult, check_paths, check_stdin, staged_python_files
from .fixes import fix_file
from .formatting import format_github, format_json, format_text
from .rule_candidates import CandidateRule
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
    check.add_argument("--signatures-path", help="Private/internal library_signatures.json to use for this check.")
    check.add_argument("--config", help="Path to llm-code-validator policy config JSON.")
    check.add_argument("--ai-review", action="store_true", help="Opt in to advisory AI review.")
    check.add_argument(
        "--ai-provider",
        choices=["openai", "anthropic", "azure-openai", "local"],
        default="openai",
        help="Provider to use for opt-in AI review.",
    )
    check.add_argument("--ai-key-env", help="Environment variable containing the provider API key.")
    check.add_argument("--ai-endpoint", help="Endpoint for local or private AI providers.")
    check.add_argument("--ai-audit-log", help="Append AI review audit metadata to this JSONL file.")
    check.add_argument("--no-network", action="store_true", help="Guarantee no provider network calls are made.")
    check.add_argument(
        "--show-ai-payload",
        action="store_true",
        help="Print the minimized, redacted AI review payload instead of sending it.",
    )
    check.add_argument("--max-snippet-lines", type=int, default=30, help="Maximum snippet lines per file for AI review.")

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
    candidate = subparsers.add_parser("suggest-rule", help="Generate a reviewed candidate rule JSON snippet.")
    candidate.add_argument("--library", required=True, help="Library name.")
    candidate.add_argument("--symbol", required=True, help="Stale API symbol.")
    candidate.add_argument("--current-version", default="current", help="Current library version label.")
    candidate.add_argument("--removed-in", help="Version where the API was removed.")
    candidate.add_argument("--changed-in", help="Version where the API changed.")
    candidate.add_argument("--reason", required=True, help="Why the API is stale.")
    candidate.add_argument("--replacement", help="Suggested replacement.")
    candidate.add_argument("--evidence", required=True, help="Official docs, release note, or maintainer discussion URL.")
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
                    signatures_path=args.signatures_path,
                )
            elif args.paths == ["-"]:
                result = check_stdin(
                    args.requirements,
                    args.python_version,
                    args.show_low_confidence,
                    args.signatures_path,
                )
            elif args.paths:
                result = check_paths(
                    args.paths,
                    args.requirements,
                    args.python_version,
                    args.show_low_confidence,
                    args.signatures_path,
                )
            else:
                parser.error("check requires a path, '-', or --staged")
            output = _render(result, args.format)
            if output:
                print(output)
            if args.ai_review:
                app_config = load_config(args.config, start=args.paths[0] if args.paths else ".")
                validate_provider_allowed(args.ai_provider, app_config)
                no_network = args.no_network or app_config.policy.no_network
                payload_paths = staged_python_files() if args.staged else args.paths
                if args.paths == ["-"]:
                    raise RuntimeError("--ai-review does not support stdin; write code to a file first")
                payload = build_ai_payload(
                    payload_paths,
                    max_snippet_lines=args.max_snippet_lines,
                    redact=True,
                )
                if args.ai_audit_log:
                    write_ai_audit_log(args.ai_audit_log, args.ai_provider, payload)
                if args.show_ai_payload:
                    print(render_ai_payload(payload))
                else:
                    print(
                        "warning: AI review may send minimized, redacted code snippets to the configured provider.",
                        file=sys.stderr,
                    )
                    key_env = args.ai_key_env or default_key_env(args.ai_provider)
                    validate_ai_provider(
                        ProviderConfig(args.ai_provider, key_env, args.ai_endpoint),
                        no_network,
                    )
                    print("AI review provider calls are not implemented yet; payload generation is ready.")
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
        if args.command == "suggest-rule":
            if not (args.evidence.startswith("https://") or args.evidence.startswith("http://")):
                raise RuntimeError("--evidence must be an official URL for candidate rules")
            if not args.removed_in and not args.changed_in:
                raise RuntimeError("suggest-rule requires --removed-in or --changed-in")
            print(
                CandidateRule(
                    library=args.library,
                    symbol=args.symbol,
                    current_version=args.current_version,
                    reason=args.reason,
                    evidence=args.evidence,
                    replacement=args.replacement,
                    removed_in=args.removed_in,
                    changed_in=args.changed_in,
                ).to_json()
            )
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
