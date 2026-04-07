from agent.schemas import ValidationIssue, ValidationReport

CONFIDENCE_THRESHOLD = 0.75


def _collect_raw_findings(state: dict) -> list:
    """
    Collect findings from all active validation paths.
    Keeps report generation compatible with both legacy and specialist flows.
    """
    findings = []
    findings.extend(state.get("issues", []))
    findings.extend(state.get("import_specialist_findings", []))
    findings.extend(state.get("method_specialist_findings", []))
    return findings


def _parse_issues(raw_findings: list) -> list[ValidationIssue]:
    """
    Parse raw finding payloads into ValidationIssue models.
    Invalid LLM outputs are ignored so one malformed issue does not break the report.
    """
    parsed_issues = []
    for finding in raw_findings:
        if isinstance(finding, ValidationIssue):
            parsed_issues.append(finding)
            continue

        if isinstance(finding, dict):
            try:
                parsed_issues.append(ValidationIssue(**finding))
            except Exception:
                continue

    return parsed_issues


def _deduplicate_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """
    Remove duplicate issue cards emitted by different specialists.
    Duplicates are keyed by the user-visible issue payload rather than hidden metadata.
    """
    seen = set()
    deduplicated = []

    for issue in issues:
        key = (
            issue.line_number,
            issue.issue_type,
            issue.original_code,
            issue.corrected_code,
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(issue)

    return deduplicated


def generate_report_node(state: dict) -> dict:
    """
    NODE 5: Package all results into the final structured report.
    
    What it does: Takes raw data from all previous nodes and
    creates a clean, typed ValidationReport. This is what the
    API endpoint returns to the user.
    
    Why Pydantic: Ensures the output always has consistent structure.
    Frontend and API consumers can always rely on the same fields.
    """

    parsed_issues = _parse_issues(_collect_raw_findings(state))
    confident_issues = [
        issue for issue in parsed_issues
        if issue.confidence >= CONFIDENCE_THRESHOLD
    ]
    deduplicated_issues = _deduplicate_issues(confident_issues)

    overall_confidence = (
        sum(issue.confidence for issue in deduplicated_issues) / len(deduplicated_issues)
        if deduplicated_issues else 1.0
    )

    if deduplicated_issues:
        summary = (
            f"Validation found {len(deduplicated_issues)} issue(s) across "
            f"{len(state.get('libraries_checked', []))} known librar"
            f"{'y' if len(state.get('libraries_checked', [])) == 1 else 'ies'}."
        )
    elif state.get("summary"):
        summary = state["summary"]
    else:
        summary = "Validation complete. No high-confidence issues found."

    report = ValidationReport(
        issues=deduplicated_issues,
        corrected_full_code=state.get("corrected_code") or state["original_code"],
        libraries_checked=state.get("libraries_checked", []),
        libraries_unknown=state.get("libraries_unknown", []),
        total_issues_found=len(deduplicated_issues),
        overall_confidence=overall_confidence,
        filtered_count=len(parsed_issues) - len(deduplicated_issues),
        summary=summary,
    )

    return {**state, "report": report.model_dump()}
