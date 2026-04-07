import json
import os
from openai import OpenAI
from agent.schemas import AgentState

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "library_signatures.json")

IMPORT_SPECIALIST_PROMPT = """You are an import path validation specialist.
Your ONLY job: determine if any import statements use old module paths
that were restructured in a breaking version change.

You receive:
- import_database_matches: entries where the import PATH changed (not the method)
- raw_imports: the exact import statements from the code

Rules:
- Only flag issues where the import MODULE PATH is wrong
- Example: "from langchain.chat_models import ChatOpenAI" is wrong — should be "from langchain_openai import ChatOpenAI"
- Do NOT flag method-level issues — that is the Method Specialist's job
- For every issue you flag, you must assign a confidence score from 0.0 to 1.0. 
- The method must explicitly be assigned a confident float, e.g. 1.0, 0.9.
- Return EXACTLY the JSON schema: {"issues": [{"line_number": int, "original_code": "...", "issue_type": "wrong_import", "explanation": "...", "corrected_code": "...", "confidence": 1.0, "library": "...", "method": "..."}]}
- The 'library' and 'method' fields must be filled so we can track what was found.

Return ONLY import path issues. Nothing else."""

def import_specialist_node(state: dict) -> dict:
    """Specialist agent focused exclusively on wrong import module paths."""
    import_matches = [
        m for m in state.get("database_results", [])
        if m.get("data") and m["data"].get("old_import") and m["data"].get("new_import")
    ]

    import_ast_items = [{"library": c["library"], "import_path": c["import_path"]} for c in state.get("extracted_calls", [])]

    if not import_matches:
        return {**state, "import_specialist_findings": []}

    client = OpenAI(timeout=60.0)
    
    # Matches are already dicts
    context = {"imports_in_code": import_ast_items, "import_database_matches": import_matches}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            messages=[
                {"role": "system", "content": IMPORT_SPECIALIST_PROMPT},
                {"role": "user", "content": f"Validate these imports:\n{json.dumps(context, indent=2)}"}
            ],
            response_format={"type": "json_object"}
        )
        findings = json.loads(response.choices[0].message.content)
        return {**state, "import_specialist_findings": findings.get("issues", [])}
    except Exception as e:
        print(f"Import specialist failed: {e}")
        return {**state, "import_specialist_findings": []}
