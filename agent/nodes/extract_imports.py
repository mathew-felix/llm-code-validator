import ast
from agent.schemas import AgentState, ExtractedCall


def extract_imports_node(state: dict) -> dict:
    """
    NODE 1: Extract every library call from the code.

    What it does: Reads the code using Python's AST parser,
    finds every import statement AND method/attribute call, and returns
    a structured list of {library, method, line_number, import_path}.

    Why AST: Handles all valid Python syntax including aliases,
    multi-line imports, and nested calls.
    """
    code = state["original_code"]
    extracted_calls = []
    alias_map = {}  # maps alias/used-name → real top-level library name

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"Syntax error in code: {e}")
        return {**state, "extracted_calls": []}

    # --- Pass 1: Collect imports and build alias map ---
    for node in ast.walk(tree):

        # Handle: from langchain.agents import initialize_agent
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            relative_prefix = "." * node.level
            library_root = module.split(".")[0] if module else ""
            library = f"{relative_prefix}{library_root}" if relative_prefix else library_root

            for alias in node.names:
                method_name = alias.name
                used_name = alias.asname if alias.asname else alias.name
                import_module = f"{relative_prefix}{module}" if module else relative_prefix
                import_path = f"from {import_module} import {method_name}"

                # Track what name is used in code → which library it belongs to
                alias_map[used_name] = library

                call = ExtractedCall(
                    library=library,
                    method=method_name,
                    line_number=node.lineno,
                    import_path=import_path
                )
                extracted_calls.append(call)

        # Handle: import numpy as np / import pinecone
        elif isinstance(node, ast.Import):
            for alias in node.names:
                library = alias.name.split(".")[0]
                used_name = alias.asname if alias.asname else alias.name

                # Build alias map: np → numpy, pd → pandas, tf → tensorflow
                alias_map[used_name] = library

                call = ExtractedCall(
                    library=library,
                    method=alias.name,
                    line_number=node.lineno,
                    import_path=f"import {alias.name}"
                )
                extracted_calls.append(call)

    # --- Pass 2: Extract method/attribute calls on imported names ---
    # Only extract calls where the caller is a known import (avoids noise)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            # Handle one-level: np.bool, pinecone.init(), df.append()
            if isinstance(node.value, ast.Name):
                caller = node.value.id
                attr = node.attr

                # Only extract if caller was actually imported
                if caller in alias_map:
                    real_library = alias_map[caller]
                    # Preserve the caller syntax for DB matching
                    # e.g., "np.bool", "pinecone.init", "tf.Session"
                    method_key = f"{caller}.{attr}"

                    call = ExtractedCall(
                        library=real_library,
                        method=method_key,
                        line_number=node.lineno,
                        import_path=f"attribute: {caller}.{attr}"
                    )
                    extracted_calls.append(call)

    # Remove duplicates (same library.method pair)
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
