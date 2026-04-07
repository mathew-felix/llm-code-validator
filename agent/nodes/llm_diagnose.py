import json
import os
from openai import OpenAI
from pydantic import ValidationError
from agent.schemas import AgentState, ValidationIssue


# The most important prompt in the entire project
DIAGNOSIS_PROMPT = """You are a Python code validator. Your job is to identify API issues in AI-generated code.

You will receive:
1. The original code to validate
2. Extracted library calls with their line numbers
3. Database results showing known issues with specific methods
4. PyPI metadata for any libraries not in our database

STRICT RULES:
- You may ONLY flag an issue if it appears in database_matches or pypi_data
- You may NOT use your own training knowledge about APIs
- You may NOT flag something as "potentially deprecated" or "might be wrong"
- If you are not certain based on the evidence given, do NOT flag it
- Every issue you report MUST cite which database entry or PyPI field proves the issue exists
- It is better to miss an issue than to invent one.
- If pypi_data for a library says "found": true, that package EXISTS and must NOT be
  labeled as a hallucinated import just because it is missing from the local database.
- If a package exists on PyPI but you do not have database evidence for a specific
  method problem, do not flag that method.

CONFIDENCE SCORING (MANDATORY):
For every issue you flag, you must assign a confidence score from 0.0 to 1.0.
Score meaning:
- 1.0 = The deprecated method is explicitly named in the database entry AND appears verbatim in the code. You are certain.
- 0.8 = The method appears in the code AND matches a database entry but the context is slightly ambiguous.
- 0.6 = You believe this is deprecated based on the database but the exact call pattern is not a perfect match.
- Below 0.6 = Do not include this issue at all.

When in doubt, score lower. A lower score that gets filtered is better than a high score on a wrong issue.

For each issue you find, classify it as exactly ONE of:
- "hallucinated": the method or library never existed
- "deprecated": the method existed but was removed in a specific version  
- "wrong_signature": the method exists but is being called with wrong arguments
- "wrong_import": the method exists but is being imported from the wrong module

Return ONLY valid JSON in this exact format — no other text:
{
    "issues": [
        {
            "line_number": <integer>,
            "original_code": "<the exact problematic line>",
            "issue_type": "<hallucinated|deprecated|wrong_signature|wrong_import>",
            "explanation": "<plain English: what is wrong, why it is wrong, when it changed>",
            "corrected_code": "<the exact fixed version of the line>",
            "confidence": <float between 0.0 and 1.0>
        }
    ],
    "corrected_full_code": "<the complete code with all fixes applied>",
    "summary": "<one paragraph plain English summary of all issues found>"
}

If no issues are found based on the provided evidence, return issues as an empty list [].
"""


def _line_from_code(original_code: str, line_number: int) -> str:
    """
    Return one source line by 1-based line number.
    Falls back to an empty string when the requested line is out of range.
    """
    code_lines = original_code.splitlines()
    if 1 <= line_number <= len(code_lines):
        return code_lines[line_number - 1]
    return ""


def _preserve_indentation(original_line: str, replacement_line: str) -> str:
    """
    Keep the original leading indentation when inserting a replacement line.
    This avoids breaking block structure in deterministic corrected_full_code output.
    """
    if not replacement_line:
        return replacement_line
    leading_spaces = len(original_line) - len(original_line.lstrip(" "))
    return f"{' ' * leading_spaces}{replacement_line.lstrip()}"


def _apply_line_corrections(original_code: str, issues: list[dict]) -> str:
    """
    Apply one-line corrections to build corrected_full_code for fallback mode.
    Keeps unchanged lines intact when no safe deterministic replacement exists.
    """
    code_lines = original_code.splitlines()
    for issue in issues:
        corrected_code = issue.get("corrected_code", "")
        line_number = issue.get("line_number", 0)
        if not corrected_code:
            continue
        if not 1 <= line_number <= len(code_lines):
            continue
        code_lines[line_number - 1] = _preserve_indentation(
            code_lines[line_number - 1],
            corrected_code,
        )
    corrected_full_code = "\n".join(code_lines)
    if original_code.endswith("\n"):
        corrected_full_code += "\n"
    return corrected_full_code


def _build_database_issue(result: dict, original_code: str) -> dict | None:
    """
    Build a high-confidence issue from a direct database hit.
    Only emits issues when the database already proves a concrete breakage.
    """
    if result.get("status") != "found_broken":
        return None

    data = result.get("data") or {}
    line_number = result.get("line_number", 0)
    original_line = _line_from_code(original_code, line_number)
    if not original_line:
        return None

    issue_type = None
    explanation = ""
    corrected_code = ""
    confidence = 1.0

    if data.get("old_import") and data.get("new_import"):
        issue_type = "wrong_import"
        explanation = (
            f"{result['method']} moved from {data['old_import']} to {data['new_import']}. "
            f"{data.get('note') or data.get('reason', '')}".strip()
        )
        corrected_code = data["new_import"]
    elif data.get("module_old") and data.get("module_current"):
        issue_type = "wrong_import"
        explanation = (
            f"{result['method']} moved from {data['module_old']} to {data['module_current']}. "
            f"{data.get('note') or data.get('reason', '')}".strip()
        )
        corrected_code = (
            original_line.replace(data["module_old"], data["module_current"])
            if data["module_old"] in original_line
            else original_line
        )
    elif data.get("signature") and data.get("correct_usage"):
        issue_type = "wrong_signature"
        explanation = (
            f"{result['method']} now expects a different signature. "
            f"{data.get('note') or data.get('reason', '')}".strip()
        )
        corrected_code = data["correct_usage"]
    elif data.get("exists") is False or data.get("changed_in"):
        issue_type = "deprecated"
        version = data.get("removed_in") or data.get("changed_in", "a newer release")
        details = data.get("reason") or data.get("note", "")
        explanation = f"{result['method']} is no longer valid in {version}. {details}".strip()
        corrected_code = (
            data.get("replacement")
            or data.get("new_usage")
            or data.get("correct_usage")
            or ""
        )
        confidence = 1.0 if data.get("exists") is False else 0.9

    if not issue_type:
        return None

    if corrected_code:
        corrected_code = _preserve_indentation(original_line, corrected_code)

    return {
        "line_number": line_number,
        "original_code": original_line,
        "issue_type": issue_type,
        "explanation": explanation,
        "corrected_code": corrected_code,
        "confidence": confidence,
    }


def _build_pypi_issue(call: dict, pypi_metadata: dict, original_code: str) -> dict | None:
    """
    Build a deterministic hallucinated-import issue from a negative PyPI result.
    Only import statements are emitted to avoid flagging downstream attribute use twice.
    """
    import_path = call.get("import_path", "")
    if not (import_path.startswith("import ") or import_path.startswith("from ")):
        return None

    original_line = _line_from_code(original_code, call.get("line_number", 0))
    if not original_line:
        return None

    distribution_name = pypi_metadata.get("distribution_name", call["library"])
    explanation = (
        f"The package '{distribution_name}' was not found on PyPI, so the import "
        f"'{call['library']}' is likely hallucinated."
    )
    return {
        "line_number": call["line_number"],
        "original_code": original_line,
        "issue_type": "hallucinated",
        "explanation": explanation,
        "corrected_code": "",
        "confidence": 1.0,
    }


def _build_deterministic_fallback(state: dict, error_message: str) -> dict:
    """
    Fall back to direct database and PyPI evidence when the LLM is unavailable.
    This keeps provable issues reportable under timeout or quota failures.
    """
    fallback_issues = []
    seen = set()

    for result in state.get("database_results", []):
        issue = _build_database_issue(result, state["original_code"])
        if issue is None:
            continue
        key = (
            issue["line_number"],
            issue["issue_type"],
            issue["original_code"],
            issue["corrected_code"],
        )
        if key in seen:
            continue
        seen.add(key)
        fallback_issues.append(issue)

    for call in state.get("extracted_calls", []):
        pypi_metadata = state.get("pypi_data", {}).get(call.get("library"))
        if not pypi_metadata or pypi_metadata.get("found") is not False:
            continue
        issue = _build_pypi_issue(call, pypi_metadata, state["original_code"])
        if issue is None:
            continue
        key = (
            issue["line_number"],
            issue["issue_type"],
            issue["original_code"],
            issue["corrected_code"],
        )
        if key in seen:
            continue
        seen.add(key)
        fallback_issues.append(issue)

    corrected_code = _apply_line_corrections(state["original_code"], fallback_issues)
    overall_confidence = (
        sum(issue["confidence"] for issue in fallback_issues) / len(fallback_issues)
        if fallback_issues else 1.0
    )

    if fallback_issues:
        summary = (
            f"Validation used deterministic fallback after an LLM error and found "
            f"{len(fallback_issues)} provable issue(s)."
        )
    else:
        summary = (
            "Validation used deterministic fallback after an LLM error and found no "
            "provable issues from database or PyPI evidence."
        )

    return {
        **state,
        "issues": fallback_issues,
        "corrected_code": corrected_code,
        "confidence": overall_confidence,
        "summary": f"{summary} Root LLM error: {error_message}",
    }


def llm_diagnose_node(state: dict) -> dict:
    """
    NODE 4: LLM reasons about all the data collected so far.
    
    What it does: Sends all collected data to GPT-4o-mini with
    a strict prompt that prevents it from using its own API knowledge.
    The LLM classifies each issue and generates corrected code.
    
    Why GPT-4o-mini and not GPT-4o:
    Classification + code correction does not require GPT-4o's
    reasoning depth. Using mini saves 33x on API costs.
    """
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=60.0)
    
    # Build the user message with all collected data
    user_message = f"""
ORIGINAL CODE TO VALIDATE:
```python
{state['original_code']}
```

EXTRACTED LIBRARY CALLS:
{json.dumps(state['extracted_calls'], indent=2)}

DATABASE RESULTS (from our curated library database):
{json.dumps(state['database_results'], indent=2)}

PYPI METADATA (for libraries not in our database):
{json.dumps(state.get('pypi_data', {}), indent=2)}

Now validate the code using ONLY the data above. Return JSON only.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": DIAGNOSIS_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,        # Low temperature = more consistent, less creative
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        raw_output = response.choices[0].message.content
        diagnosis_data = json.loads(raw_output)

        libraries_found_on_pypi = {
            library_name
            for library_name, metadata in state.get("pypi_data", {}).items()
            if metadata.get("found") is True
        }

        # Validate the LLM's output against our Pydantic schema
        issues = []
        for issue_data in diagnosis_data.get("issues", []):
            if issue_data.get("issue_type") == "hallucinated":
                matching_calls = [
                    call for call in state.get("extracted_calls", [])
                    if call.get("line_number") == issue_data.get("line_number")
                ]
                if any(
                    call.get("library") in libraries_found_on_pypi
                    for call in matching_calls
                ):
                    continue

            try:
                issue = ValidationIssue(**issue_data)
                issues.append(issue.model_dump())
            except ValidationError as e:
                print(f"LLM returned malformed issue, skipping: {e}")
                continue
        
        overall_confidence = (
            sum(i["confidence"] for i in issues) / len(issues)
            if issues else 1.0  # No issues = high confidence (confident code is clean)
        )
        
        return {
            **state,
            "issues": issues,
            "corrected_code": diagnosis_data.get("corrected_full_code", state["original_code"]),
            "confidence": overall_confidence,
            "summary": diagnosis_data.get("summary", "Validation complete.")
        }
    
    except Exception as e:
        print(f"LLM diagnosis failed: {e}")
        return _build_deterministic_fallback(state, str(e))
