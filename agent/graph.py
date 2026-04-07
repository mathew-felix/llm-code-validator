import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from agent.nodes.extract_imports import extract_imports_node
from agent.nodes.check_database import check_database_node
from agent.nodes.fetch_pypi import fetch_pypi_node
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
            "fetch_pypi": "fetch_pypi",       # If returns "fetch_pypi" → go here
            "llm_diagnose": "llm_diagnose"    # If returns "llm_diagnose" → go here
        }
    )
    
    # After PyPI fetch, always go to diagnosis
    graph.add_edge("fetch_pypi", "llm_diagnose")
    
    # After diagnosis, generate report
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
        "summary": "",
        "report": None
    }
    
    result = graph.invoke(initial_state)
    return result
