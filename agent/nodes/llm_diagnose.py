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

STRICT RULES — YOU MUST FOLLOW THESE:
- You may ONLY reason from the data provided in this prompt
- You must NEVER use your own training knowledge about library APIs
- If the database says a method does not exist, flag it — even if you think it exists
- If a library is not in the database and was NOT found on PyPI, flag the import as potentially hallucinated
- If confidence is below 0.6, say so honestly — do not guess
- Only flag issues you have evidence for from the provided data

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

If no issues are found, return issues as an empty list [].
"""


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
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30.0)
    
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
        
        # Validate the LLM's output against our Pydantic schema
        issues = []
        for issue_data in diagnosis_data.get("issues", []):
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
        return {
            **state,
            "issues": [],
            "corrected_code": state["original_code"],
            "confidence": 0.0,
            "summary": f"Validation failed due to LLM error: {str(e)}"
        }
