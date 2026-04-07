import json
from openai import OpenAI
from agent.schemas import AgentState

SUPERVISOR_PROMPT = """You are a code validation supervisor.
Your job: read a Python code snippet and decide which specialist
validation agents need to run.

Available specialists:
- "import_specialist": detects wrong import module paths (restructured packages)
- "method_specialist": detects deprecated method calls (removed methods)

Based on what you see in the code, return a JSON with:
{
  "specialists_needed": ["import_specialist", "method_specialist"],
  "reasoning": "Code uses langchain and pandas — both have known restructuring"
}

Only include specialists that are relevant to what is actually in the code.
If the code has no imports from known libraries, return an empty list."""

def supervisor_node(state: dict) -> dict:
    """Supervisor agent that routes queries dynamically to specialists."""
    client = OpenAI(timeout=60.0)

    libraries_detected = list(set(
        c["library"] for c in state.get("extracted_calls", [])
    ))

    code_summary = {
        "libraries_detected": libraries_detected,
        "database_matches": [r["status"] for r in state.get("database_results", [])]
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": SUPERVISOR_PROMPT},
                {"role": "user", "content": f"Code analysis:\n{json.dumps(code_summary, indent=2)}"}
            ],
            response_format={"type": "json_object"}
        )
        decision = json.loads(response.choices[0].message.content)
        return {
            **state,
            "specialists_needed": decision.get("specialists_needed", []),
            "supervisor_reasoning": decision.get("reasoning", "")
        }
    except Exception as e:
        print(f"Supervisor failed: {e}")
        return {
            **state,
            "specialists_needed": ["import_specialist", "method_specialist"],
            "supervisor_reasoning": "Fallback routing due to supervisor error"
        }
