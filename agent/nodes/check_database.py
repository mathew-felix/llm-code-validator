import json
import os
from agent.schemas import AgentState, DatabaseResult


def check_database_node(state: dict) -> dict:
    """
    NODE 2: Check every extracted call against our curated database.
    
    What it does: For each {library, method} pair found in the code,
    looks up our library_signatures.json to see if there are known issues.
    
    Outputs:
    - database_results: what we found for each method
    - needs_pypi_fetch: True if any library was NOT in our database
    
    This is the fast path — no API calls, no LLM. Pure lookup.
    """
    
    # Load the database you built in Phase 2
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "library_signatures.json")
    
    with open(db_path, "r") as f:
        database = json.load(f)
    
    extracted_calls = state["extracted_calls"]
    database_results = []
    needs_pypi_fetch = False
    libraries_checked = []
    libraries_unknown = []
    
    for call in extracted_calls:
        library = call["library"]
        method = call["method"]
        
        if library in database:
            # Library is in our database
            if library not in libraries_checked:
                libraries_checked.append(library)
            
            lib_data = database[library]
            methods_db = lib_data.get("methods", {})
            
            if method in methods_db:
                method_data = methods_db[method]
                
                # Check if the method has issues
                if not method_data.get("exists", True):
                    # Method was removed or deprecated
                    status = "found_broken"
                else:
                    # Method exists but might have notes (e.g., moved module)
                    has_issues = (
                        "module_old" in method_data or
                        "changed_in" in method_data
                    )
                    status = "found_broken" if has_issues else "found_ok"
                
                result = DatabaseResult(
                    library=library,
                    method=method,
                    line_number=call["line_number"],
                    status=status,
                    data=method_data
                )
            else:
                # Library is in database but this specific method isn't
                # Could be fine (not every method needs to be in DB)
                result = DatabaseResult(
                    library=library,
                    method=method,
                    line_number=call["line_number"],
                    status="not_in_db",
                    data=None
                )
        else:
            # Library not in our database at all
            if library not in libraries_unknown:
                libraries_unknown.append(library)
            needs_pypi_fetch = True
            
            result = DatabaseResult(
                library=library,
                method=method,
                line_number=call["line_number"],
                status="library_unknown",
                data=None
            )
        
        database_results.append(result.model_dump())
    
    broken_count = sum(1 for r in database_results if r["status"] == "found_broken")
    print(f"Database check: {broken_count} issues found, {len(libraries_unknown)} unknown libraries")
    
    return {
        **state,
        "database_results": database_results,
        "needs_pypi_fetch": needs_pypi_fetch,
        "libraries_checked": libraries_checked,
        "libraries_unknown": libraries_unknown
    }
