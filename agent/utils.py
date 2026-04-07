import sys


STDLIB_COMMON = {
    "__future__",
    "abc",
    "argparse",
    "ast",
    "asyncio",
    "base64",
    "collections",
    "concurrent",
    "configparser",
    "contextlib",
    "copy",
    "csv",
    "dataclasses",
    "datetime",
    "decimal",
    "dis",
    "email",
    "enum",
    "fractions",
    "functools",
    "gc",
    "hashlib",
    "http",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "multiprocessing",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "pprint",
    "random",
    "re",
    "shutil",
    "socket",
    "sqlite3",
    "statistics",
    "string",
    "struct",
    "subprocess",
    "sys",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "token",
    "tokenize",
    "traceback",
    "typing",
    "unittest",
    "urllib",
    "warnings",
    "weakref",
    "xml",
    "zipfile",
}

KNOWN_THIRD_PARTY_PREFIXES = (
    "anthropic",
    "chromadb",
    "crewai",
    "fastapi",
    "keras",
    "langchain",
    "langgraph",
    "llama",
    "numpy",
    "openai",
    "pandas",
    "pinecone",
    "pydantic",
    "sklearn",
    "sqlalchemy",
    "tensorflow",
    "torch",
    "transformers",
)


def is_likely_local_module(library_name: str, import_path: str = "") -> bool:
    """
    Return True when an import is probably local, relative, or stdlib.
    Prevents internal modules from being sent to PyPI and mislabeled as hallucinations.
    """
    normalized_name = (library_name or "").strip()
    normalized_path = (import_path or "").strip()

    if not normalized_name:
        return True

    if normalized_name.startswith(".") or normalized_path.startswith("from ."):
        return True

    top_level = normalized_name.lstrip(".").split(".")[0]

    if not top_level:
        return True

    if top_level.startswith("_"):
        return True

    if hasattr(sys, "stdlib_module_names"):
        if top_level in sys.stdlib_module_names:
            return True
    elif top_level in STDLIB_COMMON:
        return True

    # Heuristic for repo-local snake_case helpers like dual_timeline or config_schema.
    if "_" in top_level and not top_level.startswith(KNOWN_THIRD_PARTY_PREFIXES):
        return True

    return False
