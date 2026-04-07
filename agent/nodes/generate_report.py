from agent.schemas import AgentState, ValidationReport, ValidationIssue


def generate_report_node(state: dict) -> dict:
    """
    NODE 5: Package all results into the final structured report.
    
    What it does: Takes raw data from all previous nodes and
    creates a clean, typed ValidationReport. This is what the
    API endpoint returns to the user.
    
    Why Pydantic: Ensures the output always has consistent structure.
    Frontend and API consumers can always rely on the same fields.
    """
    
    issues = [ValidationIssue(**i) for i in state.get("issues", [])]
    
    report = ValidationReport(
        issues=issues,
        corrected_full_code=state.get("corrected_code", state["original_code"]),
        libraries_checked=state.get("libraries_checked", []),
        libraries_unknown=state.get("libraries_unknown", []),
        total_issues_found=len(issues),
        overall_confidence=state.get("confidence", 0.0),
        summary=state.get("summary", "Validation complete.")
    )
    
    return {**state, "report": report.model_dump()}
