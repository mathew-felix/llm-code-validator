from pathlib import Path

from scripts.evaluate_external_repos import load_repo_urls, repo_slug, summarize_diagnostics


def test_repo_slug_uses_owner_and_name() -> None:
    assert repo_slug("https://github.com/example/project.git") == "example__project"


def test_load_repo_urls_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    repos_file = tmp_path / "repos.txt"
    repos_file.write_text(
        "\n# comment\nhttps://github.com/example/one\n\nhttps://github.com/example/two\n",
        encoding="utf-8",
    )
    assert load_repo_urls(repos_file) == [
        "https://github.com/example/one",
        "https://github.com/example/two",
    ]


def test_summarize_diagnostics_groups_findings() -> None:
    summary = summarize_diagnostics(
        [
            {"library": "langchain", "symbol": "LLMChain", "code": "LCV001"},
            {"library": "langchain", "symbol": "LLMChain", "code": "LCV001"},
            {"library": "openai", "symbol": "ChatCompletion.create", "code": "LCV001"},
        ]
    )
    assert summary["by_library"] == {"langchain": 2, "openai": 1}
    assert summary["top_symbols"]["langchain.LLMChain"] == 2
