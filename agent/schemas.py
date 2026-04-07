from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ExtractedCall(BaseModel):
    """One library call found in the code"""
    library: str                    # e.g., "langchain"
    method: str                     # e.g., "initialize_agent"
    line_number: int                # which line in the code
    import_path: str                # e.g., "from langchain.agents import initialize_agent"


class DatabaseResult(BaseModel):
    """Result of checking one method against our database"""
    library: str
    method: str
    line_number: int
    status: Literal["found_broken", "found_ok", "not_in_db", "library_unknown"]
    data: Optional[dict] = None     # The database entry if found


class ValidationIssue(BaseModel):
    """One problem found in the code"""
    line_number: int
    original_code: str              # The problematic line
    issue_type: Literal[
        "hallucinated",             # method never existed
        "deprecated",               # method was removed
        "wrong_signature",          # method exists, wrong arguments
        "wrong_import"              # method exists, wrong module path
    ]
    explanation: str                # Plain English: what is wrong and why
    corrected_code: str             # The fixed version of the line
    confidence: float               # 0.0 to 1.0 — how sure the agent is


class ValidationReport(BaseModel):
    """Final output of the entire agent"""
    issues: List[ValidationIssue]
    corrected_full_code: str        # The entire code with all fixes applied
    libraries_checked: List[str]    # Libraries successfully validated
    libraries_unknown: List[str]    # Libraries not in our database (honest)
    total_issues_found: int
    overall_confidence: float
    filtered_count: int = 0         # How many low-confidence false positives were suppressed
    summary: str                    # One paragraph plain English summary


class AgentState(BaseModel):
    """The state that flows between every node in the LangGraph"""
    original_code: str = ""
    extracted_calls: List[ExtractedCall] = []
    database_results: List[DatabaseResult] = []
    pypi_data: dict = {}
    issues: List[ValidationIssue] = []
    corrected_code: str = ""
    libraries_checked: List[str] = []
    libraries_unknown: List[str] = []
    needs_pypi_fetch: bool = False
    confidence: float = 0.0
    specialists_needed: List[str] = []
    supervisor_reasoning: str = ""
    import_specialist_findings: List[ValidationIssue] = []
    method_specialist_findings: List[ValidationIssue] = []
    report: Optional[ValidationReport] = None
