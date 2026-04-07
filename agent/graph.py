import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from agent.nodes.extract_imports import extract_imports_node
from agent.nodes.check_database import check_database_node
from agent.nodes.fetch_pypi import fetch_pypi_node
from agent.nodes.supervisor import supervisor_node
from agent.nodes.import_specialist import import_specialist_node
from agent.nodes.method_specialist import method_specialist_node
from agent.nodes.llm_diagnose import llm_diagnose_node
from agent.nodes.generate_report import generate_report_node

load_dotenv()


def should_fetch_pypi(state: dict) -> str:
    """
    THE CONDITIONAL ROUTER — This is why we use LangGraph.
    
    Decision: Does the agent need to call the PyPI API?
    
    If YES: Some libraries are not in our database.
             Go to fetch_pypi node before diagnosis.
    
    If NO:  All libraries are in our database.
            Skip the API call entirely — go straight to diagnosis.
            This saves time and money on every call where
            all libraries are known.
    
    A LangChain chain cannot make this decision.
    A LangGraph conditional edge can.
    """
    if state.get("needs_pypi_fetch", False):
        return "fetch_pypi"
    else:
        return "supervisor"

def route_to_import_specialist(state: dict) -> str:
    """Check if supervisor requested the import specialist."""
    if "import_specialist" in state.get("specialists_needed", []):
        return "import_specialist"
    return "skip"

def route_to_method_specialist(state: dict) -> str:
    """Check if supervisor requested the method specialist."""
    if "method_specialist" in state.get("specialists_needed", []):
        return "method_specialist"
    return "llm_diagnose"


def build_graph():
    """
    Build and compile the LangGraph agent.
    
    Flow:
    extract_imports
        → check_database
        → [conditional] fetch_pypi (only if needed) OR llm_diagnose
        → llm_diagnose
        → generate_report
        → END
    """
    
    # Initialize the graph with a plain dict state
    # (LangGraph works with TypedDict or plain dict)
    graph = StateGraph(dict)
    
    # Add all nodes
    graph.add_node("extract_imports", extract_imports_node)
    graph.add_node("check_database", check_database_node)
    graph.add_node("fetch_pypi", fetch_pypi_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("import_specialist", import_specialist_node)
    graph.add_node("method_specialist", method_specialist_node)
    graph.add_node("llm_diagnose", llm_diagnose_node)
    graph.add_node("generate_report", generate_report_node)
    
    # Set the starting node
    graph.set_entry_point("extract_imports")
    
    # Linear edges (always run in this order)
    graph.add_edge("extract_imports", "check_database")
    
    # Conditional edge — THE DECISION POINT
    graph.add_conditional_edges(
        "check_database",           # From this node
        should_fetch_pypi,          # Call this function to decide
        {
            "fetch_pypi": "fetch_pypi",       
            "supervisor": "supervisor"    
        }
    )
    
    # After PyPI fetch, always go to supervisor
    graph.add_edge("fetch_pypi", "supervisor")
    
    # After supervisor, linearly check if we need import specialist
    graph.add_conditional_edges(
        "supervisor",
        route_to_import_specialist,
        {
            "import_specialist": "import_specialist",
            "skip": "route_to_method_node"
        }
    )
    
    # Create a passthrough node to act as the method entry point
    def passthrough(state): return state
    graph.add_node("route_to_method_node", passthrough)
    
    graph.add_edge("import_specialist", "route_to_method_node")
    
    graph.add_conditional_edges(
        "route_to_method_node",
        route_to_method_specialist,
        {
            "method_specialist": "method_specialist",
            "llm_diagnose": "llm_diagnose"
        }
    )
    
    # Run the broad diagnosis pass after the targeted specialists
    graph.add_edge("method_specialist", "llm_diagnose")
    graph.add_edge("llm_diagnose", "generate_report")
    
    # After report, done
    graph.add_edge("generate_report", END)
    
    return graph.compile()


def validate_code(code: str) -> dict:
    """
    Main entry point for the agent.
    
    Usage:
        from agent.graph import validate_code
        result = validate_code(your_python_code_string)
        print(result['report'])
    """
    graph = build_graph()
    
    # Initial state — all fields empty, agent fills them
    initial_state = {
        "original_code": code,
        "extracted_calls": [],
        "database_results": [],
        "pypi_data": {},
        "issues": [],
        "corrected_code": "",
        "libraries_checked": [],
        "libraries_unknown": [],
        "needs_pypi_fetch": False,
        "confidence": 0.0,
        "specialists_needed": [],
        "supervisor_reasoning": "",
        "import_specialist_findings": [],
        "method_specialist_findings": [],
        "summary": "",
        "report": None
    }
    
    result = graph.invoke(initial_state)
    return result
