import ast
from typing import List
from agent.schemas import AgentState, ExtractedCall


def extract_imports_node(state: dict) -> dict:
    """
    NODE 1: Extract every library call from the code.
    
    What it does: Reads the code using Python's AST parser,
    finds every import statement and method call, and returns
    a structured list of {library, method, line_number, import_path}
    
    Why AST: Handles all valid Python syntax including aliases,
    multi-line imports, and nested calls.
    """
    code = state["original_code"]
    extracted_calls = []
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        # Code has syntax errors — cannot parse
        # Return empty list and let later nodes handle it
        print(f"Syntax error in code: {e}")
        return {**state, "extracted_calls": []}
    
    # Walk through every node in the AST
    for node in ast.walk(tree):
        
        # Handle: from langchain.agents import initialize_agent
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            library = module.split(".")[0]  # Get top-level package name
            
            for alias in node.names:
                method_name = alias.name
                import_path = f"from {module} import {method_name}"
                
                call = ExtractedCall(
                    library=library,
                    method=method_name,
                    line_number=node.lineno,
                    import_path=import_path
                )
                extracted_calls.append(call)
        
        # Handle: import langchain
        elif isinstance(node, ast.Import):
            for alias in node.names:
                library = alias.name.split(".")[0]
                call = ExtractedCall(
                    library=library,
                    method=alias.name,
                    line_number=node.lineno,
                    import_path=f"import {alias.name}"
                )
                extracted_calls.append(call)
    
    # Remove duplicates (same method imported in multiple ways)
    seen = set()
    unique_calls = []
    for call in extracted_calls:
        key = f"{call.library}.{call.method}"
        if key not in seen:
            seen.add(key)
            unique_calls.append(call)
    
    print(f"Extracted {len(unique_calls)} unique library calls")
    
    # Convert to dict for LangGraph state
    return {
        **state,
        "extracted_calls": [c.model_dump() for c in unique_calls]
    }
