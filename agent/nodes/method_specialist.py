import json
import os
from openai import OpenAI
from agent.schemas import AgentState

METHOD_SPECIALIST_PROMPT = """You are a deprecated method call specialist.
Your ONLY job: determine if any method CALLS in the code use methods that
have been removed or renamed in a breaking version change.

You receive:
- method_database_matches: database entries for removed/changed methods
- method_calls: all attribute method calls extracted from the code via AST

Rules:
- Only flag issues where a CALLED method is deprecated or removed
- The method must actually be CALLED in the code — not just imported
- Example: df.append() is a call. "from pandas import append" is an import.
- For every issue you flag, you must assign a confidence score from 0.0 to 1.0.
- Return EXACTLY the JSON schema: {"issues": [{"line_number": int, "original_code": "...", "issue_type": "deprecated", "explanation": "...", "corrected_code": "...", "confidence": 1.0, "library": "...", "method": "..."}]}
- The 'library' and 'method' fields must be filled so we can track what was found.

Return ONLY method-level deprecation or hallucination issues."""

def method_specialist_node(state: dict) -> dict:
    """Specialist agent focused on deprecated method calls on objects."""
    method_matches = [
        m for m in state.get("database_results", [])
        if m.get("data") and (m["data"].get("exists") == False or "all_known_issues_for_this_library" in m["data"])
    ]

    if not state.get("extracted_calls") or not method_matches:
        return {**state, "method_specialist_findings": []}

    client = OpenAI(timeout=60.0)
    
    # Already dicts
    context = {"method_calls_in_code": state.get("extracted_calls", []), "deprecated_method_entries": method_matches}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            messages=[
                {"role": "system", "content": METHOD_SPECIALIST_PROMPT},
                {"role": "user", "content": f"Check these method calls:\n{json.dumps(context, indent=2)}"}
            ],
            response_format={"type": "json_object"}
        )
        findings = json.loads(response.choices[0].message.content)
        return {**state, "method_specialist_findings": findings.get("issues", [])}
    except Exception as e:
        print(f"Method specialist failed: {e}")
        return {**state, "method_specialist_findings": []}
