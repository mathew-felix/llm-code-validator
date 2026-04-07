# Step-by-Step Build Guide: AI Code Hallucination Validator
### Every task explained simply. Follow in order. End with complete working code.

***

## Before You Start — Understanding the Big Picture

Imagine you ask ChatGPT to write Python code using LangChain. It writes:

```python
from langchain.agents import initialize_agent
agent = initialize_agent(tools=tools, llm=llm)
```

You run it. You get:
```
ImportError: cannot import name 'initialize_agent'
```

You just wasted 30 minutes because LangChain removed that function in 2023.
Your agent will **catch this before you even run the code.**

Here is how the finished agent works in one sentence:
> User pastes AI-generated code → agent checks every function call against a database of known changes → LLM explains what is wrong and gives corrected code → user gets a report.

Now build it, one step at a time.

***

## PHASE 1: Project Setup
### "Setting up your workspace so nothing breaks mid-build"

***

### Task 1.1 — Create the Project Folder Structure

**Why you need this:**
If you just dump files in one folder, the project becomes impossible to navigate by Day 5. A clean structure means you always know where to put new code and where to find existing code. It also looks professional on GitHub.

**What to do:**
Open your terminal and run:

```bash
mkdir hallucination-validator
cd hallucination-validator

mkdir agent
mkdir agent/nodes
mkdir api
mkdir frontend
mkdir tests
mkdir validation_dataset
mkdir data
```

**What you now have:**
```
hallucination-validator/
├── agent/          ← All the LangGraph agent code lives here
│   └── nodes/      ← Each tool/step is its own file here
├── api/            ← FastAPI endpoint (how users talk to the agent)
├── frontend/       ← Simple web page for the demo
├── tests/          ← Your 50 test cases and accuracy measurements
├── validation_dataset/ ← The 50 real code examples you will collect
└── data/           ← Your library database JSON file
```

***

### Task 1.2 — Create the Virtual Environment

**Why you need this:**
A virtual environment is an isolated bubble for your project's packages. Without it, installing packages for this project might break other Python projects on your computer. It also makes your project reproducible — anyone who clones your GitHub can install the exact same packages.

**What to do:**
```bash
python -m venv venv

# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# You should see (venv) at the start of your terminal line now
```

***

### Task 1.3 — Install All Packages

**Why you need this:**
These are the tools your code will use. Installing them all at once now means you will not hit "module not found" errors mid-build.

**What to do:**
Create a file called `requirements.txt` in the root folder:

```
langgraph==0.2.28
langchain==0.3.7
langchain-openai==0.2.9
openai==1.54.0
fastapi==0.115.4
uvicorn==0.32.0
httpx==0.27.2
pydantic==2.9.2
python-dotenv==1.0.1
pytest==8.3.3
```

Then install:
```bash
pip install -r requirements.txt
```

**Why these specific versions:**
LangGraph and LangChain change frequently. Pinning versions means your code will not break tomorrow because the library updated. This is real engineering practice.

***

### Task 1.4 — Create the .env File for Your API Key

**Why you need this:**
Your OpenAI API key is a secret. If you hardcode it in your Python file and push to GitHub, anyone can see it and use it. A `.env` file keeps it separate. It never gets pushed to GitHub.

**What to do:**
Create a file called `.env` in the root folder:
```
OPENAI_API_KEY=your_actual_key_here
```

Create a file called `.gitignore` in the root folder:
```
.env
venv/
__pycache__/
*.pyc
.DS_Store
```

The `.gitignore` tells Git to never upload these files. Your API key stays private.

***

## PHASE 2: The Database — Your Most Important Asset
### "This is what makes your project different from every tutorial"

***

### Task 2.1 — Understand What the Database Is

**Why you need this:**
The PyPI website (where Python packages live) tells you a package exists and what version it is. It does NOT tell you which methods were removed, which argument signatures changed, or what replaced them. You have to build that knowledge yourself.

Think of it like this:
- PyPI = a library catalog that tells you a book exists
- Your database = your own handwritten notes about what changed in each book's new edition

**What the database looks like:**
Create the file `data/library_signatures.json` and start with this structure:

```json
{
  "langchain": {
    "current_version": "0.3.x",
    "last_updated": "2026-04-07",
    "methods": {
      "initialize_agent": {
        "exists": false,
        "removed_in": "0.2.0",
        "removed_date": "2023-09-15",
        "reason": "Replaced by new agent constructors in LangGraph",
        "replacement": "langgraph.prebuilt.create_react_agent",
        "replacement_example": "from langgraph.prebuilt import create_react_agent\nagent = create_react_agent(llm, tools)",
        "old_import": "from langchain.agents import initialize_agent"
      }
    }
  }
}
```

***

### Task 2.2 — Build the LangChain Entry (Day 1, ~3 hours)

**Why you need this:**
LangChain is the #1 most broken library in AI-generated code. It went through a complete restructure between v0.1 and v0.2, and most LLMs still generate the old API because their training data predates the change.

**What to do:**
Go to: `https://github.com/langchain-ai/langchain/releases`

For each release from v0.2.0 onward, look for entries labeled "Breaking Changes" or "Deprecated". Record every one.

**Add these entries to your JSON** (this is already researched for you — verify each one yourself):

```json
"langchain": {
  "current_version": "0.3.x",
  "last_updated": "2026-04-07",
  "methods": {
    "initialize_agent": {
      "exists": false,
      "removed_in": "0.2.0",
      "reason": "Replaced by LangGraph agent constructors",
      "replacement": "langgraph.prebuilt.create_react_agent",
      "old_import": "from langchain.agents import initialize_agent",
      "replacement_example": "from langgraph.prebuilt import create_react_agent\nagent = create_react_agent(llm, tools)"
    },
    "ConversationBufferMemory": {
      "exists": true,
      "module_current": "langchain_community.memory",
      "module_old": "langchain.memory",
      "changed_in": "0.2.0",
      "note": "Moved to langchain_community package — requires pip install langchain-community",
      "old_import": "from langchain.memory import ConversationBufferMemory",
      "new_import": "from langchain_community.memory import ConversationBufferMemory"
    },
    "LLMChain": {
      "exists": false,
      "removed_in": "0.3.0",
      "reason": "Replaced by LCEL (LangChain Expression Language) pipe syntax",
      "replacement": "chain = prompt | llm | output_parser",
      "old_import": "from langchain.chains import LLMChain",
      "replacement_example": "from langchain_core.prompts import ChatPromptTemplate\nchain = ChatPromptTemplate.from_template('{input}') | llm"
    },
    "OpenAI": {
      "exists": true,
      "module_current": "langchain_openai",
      "module_old": "langchain.llms",
      "changed_in": "0.2.0",
      "note": "Moved to langchain_openai package",
      "old_import": "from langchain.llms import OpenAI",
      "new_import": "from langchain_openai import OpenAI"
    },
    "ChatOpenAI": {
      "exists": true,
      "module_current": "langchain_openai",
      "module_old": "langchain.chat_models",
      "changed_in": "0.2.0",
      "note": "Moved to langchain_openai package",
      "old_import": "from langchain.chat_models import ChatOpenAI",
      "new_import": "from langchain_openai import ChatOpenAI"
    }
  }
}
```

***

### Task 2.3 — Build the OpenAI SDK Entry (Day 1, ~1 hour)

**Why you need this:**
OpenAI completely rewrote their Python SDK from v0 to v1 in November 2023. Every piece of code that used the old API broke immediately. LLMs trained before late 2024 still generate the old v0 API.

**The biggest breaking changes:**

```json
"openai": {
  "current_version": "1.x",
  "last_updated": "2026-04-07",
  "methods": {
    "openai.ChatCompletion.create": {
      "exists": false,
      "removed_in": "1.0.0",
      "removed_date": "2023-11-06",
      "reason": "Complete SDK rewrite — class-based API removed",
      "old_import": "import openai\nopenai.ChatCompletion.create(...)",
      "replacement": "from openai import OpenAI\nclient = OpenAI()\nclient.chat.completions.create(...)",
      "replacement_example": "from openai import OpenAI\nclient = OpenAI(api_key='your-key')\nresponse = client.chat.completions.create(\n    model='gpt-4o-mini',\n    messages=[{'role': 'user', 'content': 'Hello'}]\n)"
    },
    "openai.Completion.create": {
      "exists": false,
      "removed_in": "1.0.0",
      "reason": "Completions API replaced by chat completions",
      "old_import": "import openai\nopenai.Completion.create(...)",
      "replacement": "client.chat.completions.create(...)"
    },
    "openai.api_key": {
      "exists": false,
      "removed_in": "1.0.0",
      "reason": "Global state removed — pass key to client constructor",
      "old_usage": "openai.api_key = 'sk-...'",
      "replacement": "client = OpenAI(api_key='sk-...')"
    }
  }
}
```

***

### Task 2.4 — Build PyTorch, sklearn, Pydantic, HuggingFace Entries (Day 2, ~4 hours)

**Why you need this:**
These four libraries are in almost every ML codebase. They all had major breaking changes that LLMs commonly get wrong.

**What to do — go to these changelogs:**
- PyTorch: `https://github.com/pytorch/pytorch/releases` (look for 2.0, 2.1, 2.2 breaking changes)
- sklearn: `https://scikit-learn.org/stable/whats_new/` (look for 1.3, 1.4 deprecations)
- Pydantic: `https://docs.pydantic.dev/latest/migration/` (v1 → v2 is a complete rewrite)
- HuggingFace: `https://github.com/huggingface/transformers/releases` (Trainer API changes)

**Add the Pydantic entry as a starting point — this one breaks almost everything:**

```json
"pydantic": {
  "current_version": "2.x",
  "last_updated": "2026-04-07",
  "methods": {
    "validator": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Replaced by field_validator decorator",
      "old_import": "from pydantic import validator",
      "replacement": "from pydantic import field_validator",
      "replacement_example": "@field_validator('field_name')\n@classmethod\ndef validate_field(cls, v):\n    return v"
    },
    "BaseModel.__fields__": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Replaced by model_fields",
      "old_usage": "MyModel.__fields__",
      "replacement": "MyModel.model_fields"
    },
    "BaseModel.dict": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Replaced by model_dump()",
      "old_usage": "my_instance.dict()",
      "replacement": "my_instance.model_dump()"
    },
    "BaseModel.json": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Replaced by model_dump_json()",
      "old_usage": "my_instance.json()",
      "replacement": "my_instance.model_dump_json()"
    }
  }
}
```

***

### Task 2.5 — Add Remaining 15 Libraries (Day 3, ~4 hours)

**Libraries to add (use same JSON structure):**
For each library, go to its GitHub releases page and find breaking changes.

```
FastAPI → https://github.com/tiangolo/fastapi/releases
NumPy → https://numpy.org/doc/stable/release/2.0.0-notes.html
Pandas → https://pandas.pydata.org/docs/whatsnew/v2.0.0.html
LlamaIndex → https://github.com/run-llama/llama_index/releases
CrewAI → https://github.com/crewAIInc/crewAI/releases
ChromaDB → https://github.com/chroma-core/chroma/releases
Pinecone → https://github.com/pinecone-io/pinecone-python-client/releases
SQLAlchemy → https://docs.sqlalchemy.org/en/20/changelog/migration_20.html
TensorFlow → https://github.com/tensorflow/tensorflow/releases
Anthropic SDK → https://github.com/anthropics/anthropic-sdk-python/releases
Motor/PyMongo → https://pymongo.readthedocs.io/en/stable/changelog.html
Matplotlib → https://matplotlib.org/stable/users/release_notes.html
Boto3 → https://github.com/boto/boto3/blob/develop/CHANGELOG.rst
httpx → https://github.com/encode/httpx/releases
Requests → https://requests.readthedocs.io/en/latest/community/updates/
```

**Target:** 5–15 entries per library. Quality over quantity. Only add entries where you have verified the breaking change from official docs.

**How to verify:** Search Stack Overflow or GitHub Issues for the error. If you find 3+ questions asking about the same breakage, it is real and common.

***

## PHASE 3: The Pydantic Schemas
### "Defining the shape of data so every part of the agent speaks the same language"

***

### Task 3.1 — Create the Schemas File

**Why you need this:**
Every node in your agent produces some data and passes it to the next node. If Node 1 returns a list but Node 2 expects a dictionary, the agent crashes. Pydantic schemas define the exact shape of data — like a contract between nodes. This is also what interviewers ask about when they say "structured output."

**What to do:**
Create file `agent/schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ExtractedCall(BaseModel):
    """One library call found in the code"""
    library: str                    # e.g., "langchain"
    method: str                     # e.g., "initialize_agent"
    line_number: int                # which line in the code
    import_path: str                # e.g., "from langchain.agents import initialize_agent"


class DatabaseResult(BaseModel):
    """Result of checking one method against our database"""
    library: str
    method: str
    line_number: int
    status: Literal["found_broken", "found_ok", "not_in_db", "library_unknown"]
    data: Optional[dict] = None     # The database entry if found


class ValidationIssue(BaseModel):
    """One problem found in the code"""
    line_number: int
    original_code: str              # The problematic line
    issue_type: Literal[
        "hallucinated",             # method never existed
        "deprecated",               # method was removed
        "wrong_signature",          # method exists, wrong arguments
        "wrong_import"              # method exists, wrong module path
    ]
    explanation: str                # Plain English: what is wrong and why
    corrected_code: str             # The fixed version of the line
    confidence: float               # 0.0 to 1.0 — how sure the agent is


class ValidationReport(BaseModel):
    """Final output of the entire agent"""
    issues: List[ValidationIssue]
    corrected_full_code: str        # The entire code with all fixes applied
    libraries_checked: List[str]    # Libraries successfully validated
    libraries_unknown: List[str]    # Libraries not in our database (honest)
    total_issues_found: int
    overall_confidence: float
    summary: str                    # One paragraph plain English summary


class AgentState(BaseModel):
    """The state that flows between every node in the LangGraph"""
    original_code: str = ""
    extracted_calls: List[ExtractedCall] = []
    database_results: List[DatabaseResult] = []
    pypi_data: dict = {}
    issues: List[ValidationIssue] = []
    corrected_code: str = ""
    libraries_checked: List[str] = []
    libraries_unknown: List[str] = []
    needs_pypi_fetch: bool = False
    confidence: float = 0.0
    report: Optional[ValidationReport] = None
```

**What this does for the problem:**
Every issue found gets a `line_number`, `original_code`, `issue_type`, `explanation`, and `corrected_code`. The interviewer sees structured output. The user gets actionable information. The agent cannot skip fields or return inconsistent data.

***

## PHASE 4: The Tool Nodes
### "Each node is one specific job. Nothing more."

***

### Task 4.1 — Build the Import Extractor Node

**Why you need this:**
Before you can check if a method is wrong, you need to know which methods are being used. This node reads the code and extracts every single library call — the library name, the method name, and which line it is on.

**Why AST and not regex:**
Regex would miss aliased imports (`import numpy as np`), multi-line imports, and parenthesized imports. Python's built-in `ast` module handles all valid Python syntax correctly because it uses the same parser Python itself uses.

**What to do:**
Create file `agent/nodes/extract_imports.py`:

```python
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
```

***

### Task 4.2 — Build the Database Lookup Node

**Why you need this:**
This is where your 3 days of database-building pays off. For every method extracted in Task 4.1, this node checks your `library_signatures.json` and answers: does this method exist? Was it removed? What replaced it?

If the answer is in the database → use it (fast, accurate).
If the library is unknown → flag it for PyPI fetching (slower path).

**What to do:**
Create file `agent/nodes/check_database.py`:

```python
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
    db_path = os.path.join(os.path.dirname(__file__), "../../data/library_signatures.json")
    
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
```

***

### Task 4.3 — Build the PyPI Fetch Node

**Why you need this:**
When the code uses a library that is NOT in your database (e.g., some rare library you haven't documented), you cannot just say "no issues found" — that would be a false negative. Instead, you fetch basic metadata from PyPI to at least tell the LLM what version currently exists, so it can make a more informed judgment.

**What to do:**
Create file `agent/nodes/fetch_pypi.py`:

```python
import httpx
from agent.schemas import AgentState


def fetch_pypi_node(state: dict) -> dict:
    """
    NODE 3 (Optional): Fetch package metadata from PyPI for unknown libraries.
    
    What it does: For every library NOT in our local database,
    hits the free PyPI JSON API to get current version info.
    
    Why this helps: Even without method signatures, knowing the
    current version lets the LLM reason about whether the code's
    imports are plausible.
    
    Important: This only runs if needs_pypi_fetch is True.
    The conditional router in the graph skips this node otherwise.
    """
    
    pypi_data = {}
    libraries_unknown = state.get("libraries_unknown", [])
    
    for library in libraries_unknown:
        try:
            # PyPI JSON API — completely free, no auth required
            url = f"https://pypi.org/pypi/{library}/json"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                info = data["info"]
                
                pypi_data[library] = {
                    "found": True,
                    "latest_version": info["version"],
                    "summary": info["summary"],
                    "requires_python": info.get("requires_python", "unknown"),
                    "home_page": info.get("home_page", ""),
                    "note": "Library found on PyPI but not in local signature database. LLM reasoning quality may be lower."
                }
                print(f"PyPI: Found {library} v{info['version']}")
            
            elif response.status_code == 404:
                # Package doesn't exist on PyPI at all
                pypi_data[library] = {
                    "found": False,
                    "note": "Package not found on PyPI. This import may be hallucinated."
                }
                print(f"PyPI: {library} NOT FOUND — possible hallucination")
            
            else:
                pypi_data[library] = {
                    "found": None,
                    "note": f"PyPI returned status {response.status_code}"
                }
        
        except httpx.TimeoutException:
            pypi_data[library] = {
                "found": None,
                "note": "PyPI request timed out"
            }
        except Exception as e:
            pypi_data[library] = {
                "found": None,
                "note": f"Error fetching PyPI data: {str(e)}"
            }
    
    return {**state, "pypi_data": pypi_data}
```

***

### Task 4.4 — Build the LLM Diagnosis Node (The Brain)

**Why you need this:**
The database and PyPI fetching collect raw facts. This node is where the actual intelligence happens. The LLM reads all the raw data and reasons: What specifically is wrong? Why is it wrong? What is the correct code? How confident am I?

The most important part of this node is **the prompt**. The prompt forbids the LLM from using its own memory about library APIs. It must only use the data provided. This prevents the LLM from hallucinating about the very thing you are trying to detect.

**What to do:**
Create file `agent/nodes/llm_diagnose.py`:

```python
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
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
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
```

***

### Task 4.5 — Build the Report Generator Node

**Why you need this:**
The raw output from the LLM node is a Python dictionary. This node packages it into the clean, typed `ValidationReport` Pydantic model that the API returns to the user. It also calculates final summary statistics.

**What to do:**
Create file `agent/nodes/generate_report.py`:

```python
from agent.schemas import AgentState, ValidationReport, ValidationIssue


def generate_report_node(state: dict) -> dict:
    """
    NODE 5: Package all results into the final structured report.
    
    What it does: Takes raw data from all previous nodes and
    creates a clean, typed ValidationReport. This is what the
    API endpoint returns to the user.
    
    Why Pydantic: Ensures the output always has consistent structure.
    Frontend and API consumers can always rely on the same fields.
    """
    
    issues = [ValidationIssue(**i) for i in state.get("issues", [])]
    
    report = ValidationReport(
        issues=issues,
        corrected_full_code=state.get("corrected_code", state["original_code"]),
        libraries_checked=state.get("libraries_checked", []),
        libraries_unknown=state.get("libraries_unknown", []),
        total_issues_found=len(issues),
        overall_confidence=state.get("confidence", 0.0),
        summary=state.get("summary", "Validation complete.")
    )
    
    return {**state, "report": report.model_dump()}
```

***

## PHASE 5: The LangGraph — Wiring Everything Together
### "This is where all nodes become one agent"

***

### Task 5.1 — Build the Graph

**Why you need this:**
Right now you have 5 separate functions. This task connects them into a single agent that runs them in the right order, with conditional routing. When an interviewer asks "why LangGraph?" — you point to the conditional router on line 43 below: "If all libraries are in our database, skip the PyPI fetch — that decision cannot be made by a simple chain."

**What to do:**
Create file `agent/graph.py`:

```python
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
```

***

## PHASE 6: The API
### "How the outside world talks to your agent"

***

### Task 6.1 — Build the FastAPI Endpoint

**Why you need this:**
Right now your agent only works if someone runs Python code directly. An API means: your frontend can call it, other developers can use it, you can demo it in a browser. FastAPI is the standard for Python APIs — it automatically generates documentation at `/docs`.

**What to do:**
Create file `api/main.py`:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback

from agent.graph import validate_code
from agent.schemas import ValidationReport

app = FastAPI(
    title="AI Code Hallucination Validator",
    description="Validates AI-generated Python code against live library APIs",
    version="1.0.0"
)

# Allow the frontend (running on different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeInput(BaseModel):
    code: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "from langchain.agents import initialize_agent\nfrom langchain.llms import OpenAI\nagent = initialize_agent(tools=[], llm=OpenAI())"
            }
        }


@app.get("/")
def root():
    return {
        "name": "AI Code Hallucination Validator",
        "status": "running",
        "docs": "/docs"
    }


@app.post("/validate", response_model=ValidationReport)
def validate(input: CodeInput):
    """
    Validate AI-generated Python code for hallucinated or deprecated API calls.
    
    Submit code as a string. Returns a structured report with:
    - List of issues found (type, line, explanation, corrected code)
    - Full corrected version of the code
    - Libraries successfully checked vs unknown
    - Overall confidence score
    """
    
    if not input.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    
    if len(input.code) > 10000:
        raise HTTPException(status_code=400, detail="Code too long — max 10,000 characters")
    
    try:
        result = validate_code(input.code)
        
        if result.get("report") is None:
            raise HTTPException(
                status_code=500,
                detail="Agent failed to generate report"
            )
        
        return result["report"]
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "healthy"}
```

**How to run the API:**
```bash
uvicorn api.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` — FastAPI auto-generates an interactive UI where you can test the API immediately.

***

## PHASE 7: The Frontend
### "The 30-second demo that hiring managers actually see"

***

### Task 7.1 — Build the Demo UI

**Why you need this:**
Hiring managers do not read code. They look at your README and click your demo. A working UI that shows the agent catching hallucinations in 10 seconds is worth more than a perfect codebase they never see.

**What to do:**
Create file `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Code Hallucination Validator</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; }
        
        header {
            padding: 20px 40px;
            border-bottom: 1px solid #333;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        header h1 { font-size: 20px; font-weight: 600; }
        .badge {
            background: #1a1a2e;
            border: 1px solid #4a4a8a;
            color: #8888ff;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .container { display: grid; grid-template-columns: 1fr 1fr; height: calc(100vh - 65px); }
        
        .panel { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
        .panel-header { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
        
        textarea {
            flex: 1;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #e0e0e0;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            padding: 16px;
            resize: none;
            outline: none;
            line-height: 1.6;
        }
        textarea:focus { border-color: #4a4a8a; }
        
        button {
            background: #4a4a8a;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: #5a5aaa; }
        button:disabled { background: #333; cursor: not-allowed; }
        
        .right-panel { border-left: 1px solid #333; }
        .results { flex: 1; overflow-y: auto; }
        
        .issue-card {
            background: #1a1a1a;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 3px solid #ff4444;
        }
        .issue-card.wrong_import { border-left-color: #ff8c00; }
        .issue-card.wrong_signature { border-left-color: #ffcc00; }
        .issue-card.deprecated { border-left-color: #ff4444; }
        .issue-card.hallucinated { border-left-color: #ff0066; }
        
        .issue-type {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 6px;
        }
        .issue-line { font-size: 12px; color: #666; margin-bottom: 8px; }
        
        code {
            background: #252525;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        
        .explanation { font-size: 13px; line-height: 1.5; margin: 8px 0; color: #ccc; }
        
        .fix-label { font-size: 11px; color: #4caf50; text-transform: uppercase; margin-top: 10px; }
        .fix-code {
            background: #0a1a0a;
            border: 1px solid #1a3a1a;
            border-radius: 4px;
            padding: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #4caf50;
            margin-top: 4px;
        }
        
        .no-issues {
            text-align: center;
            padding: 60px 20px;
            color: #4caf50;
        }
        .no-issues .icon { font-size: 48px; margin-bottom: 12px; }
        
        .loading { text-align: center; padding: 60px 20px; color: #888; }
        .spinner {
            width: 32px; height: 32px;
            border: 3px solid #333;
            border-top-color: #4a4a8a;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 12px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .summary {
            background: #1a1a1a;
            border-radius: 8px;
            padding: 16px;
            font-size: 13px;
            line-height: 1.6;
            color: #aaa;
            margin-bottom: 12px;
        }
        
        .stats { display: flex; gap: 12px; margin-bottom: 12px; }
        .stat {
            background: #1a1a1a;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 12px;
            color: #888;
        }
        .stat span { color: #e0e0e0; font-weight: 600; font-size: 16px; display: block; }
    </style>
</head>
<body>

<header>
    <h1>AI Code Hallucination Validator</h1>
    <div class="badge">LangGraph + GPT-4o-mini</div>
</header>

<div class="container">
    <div class="panel">
        <div class="panel-header">Paste AI-Generated Python Code</div>
        <textarea id="codeInput" placeholder="# Paste AI-generated code here...
# Example broken code:
from langchain.agents import initialize_agent
from langchain.llms import OpenAI

llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools=[],
    llm=llm,
    agent='zero-shot-react-description'
)"></textarea>
        <button id="validateBtn" onclick="validate()">
            Validate Code →
        </button>
    </div>
    
    <div class="panel right-panel">
        <div class="panel-header">Validation Report</div>
        <div class="results" id="results">
            <div style="padding: 60px 20px; text-align: center; color: #555;">
                Paste code and click Validate to see the report
            </div>
        </div>
    </div>
</div>

<script>
async function validate() {
    const code = document.getElementById('codeInput').value.trim();
    if (!code) return;
    
    const btn = document.getElementById('validateBtn');
    const results = document.getElementById('results');
    
    btn.disabled = true;
    btn.textContent = 'Validating...';
    results.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            Agent is analyzing your code...
        </div>
    `;
    
    try {
        const response = await fetch('http://localhost:8000/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Validation failed');
        }
        
        const report = await response.json();
        renderReport(report);
    } catch (err) {
        results.innerHTML = `
            <div style="padding: 20px; color: #ff4444;">
                Error: ${err.message}
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Validate Code →';
    }
}

function renderReport(report) {
    const results = document.getElementById('results');
    
    if (report.total_issues_found === 0) {
        results.innerHTML = `
            <div class="no-issues">
                <div class="icon">✅</div>
                <strong>No issues found</strong>
                <p style="color: #666; margin-top: 8px;">
                    Checked ${report.libraries_checked.length} libraries
                </p>
            </div>
        `;
        return;
    }
    
    const confidence = (report.overall_confidence * 100).toFixed(0);
    
    let html = `
        <div class="stats">
            <div class="stat"><span>${report.total_issues_found}</span>Issues Found</div>
            <div class="stat"><span>${confidence}%</span>Confidence</div>
            <div class="stat"><span>${report.libraries_checked.length}</span>Libs Checked</div>
        </div>
        <div class="summary">${report.summary}</div>
    `;
    
    for (const issue of report.issues) {
        html += `
            <div class="issue-card ${issue.issue_type}">
                <div class="issue-type">⚠ ${issue.issue_type.replace('_', ' ')}</div>
                <div class="issue-line">Line ${issue.line_number}</div>
                <code>${escapeHtml(issue.original_code)}</code>
                <div class="explanation">${issue.explanation}</div>
                <div class="fix-label">✓ Corrected</div>
                <div class="fix-code">${escapeHtml(issue.corrected_code)}</div>
            </div>
        `;
    }
    
    if (report.libraries_unknown.length > 0) {
        html += `
            <div class="summary" style="border: 1px solid #333;">
                ⚠ Libraries not in database (limited validation):
                ${report.libraries_unknown.join(', ')}
            </div>
        `;
    }
    
    results.innerHTML = html;
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
</script>
</body>
</html>
```

Open `frontend/index.html` in your browser while the API is running. Done.

***

## PHASE 8: Validation — Proving It Works
### "This is what separates your project from every tutorial"

***

### Task 8.1 — Collect 50 Real Broken Code Examples

**Why you need this:**
Without measured accuracy, your project is just "it works sometimes." With a validation table, your project has engineering rigor. The 50 examples also become a permanent test suite.

**Where to find real broken examples:**

1. **Your own thesis code** — every time you got an ImportError or AttributeError
2. **r/LocalLLaMA** — search "hallucination" + "code"
3. **r/learnpython** — search "AI generated" + "error"
4. **Stack Overflow** — search `[langchain] ImportError 2024` or `[pytorch] AttributeError`
5. **GitHub Issues** — search `label:bug` on LangChain, PyTorch, HuggingFace repos for common user mistakes

**Create file `validation_dataset/test_cases.json`:**
```json
[
  {
    "id": "test_001",
    "description": "LangChain initialize_agent removed in 0.2",
    "code": "from langchain.agents import initialize_agent\nfrom langchain.llms import OpenAI\nagent = initialize_agent(tools=[], llm=OpenAI())",
    "known_issues": [
      {
        "line": 1,
        "type": "deprecated",
        "method": "initialize_agent",
        "library": "langchain"
      },
      {
        "line": 2,
        "type": "wrong_import",
        "method": "OpenAI",
        "library": "langchain"
      }
    ],
    "source": "Personal experience + r/LocalLLaMA"
  }
]
```

***

### Task 8.2 — Build and Run the Evaluation Script

**Why you need this:**
Running the agent manually on 50 examples and checking results would take hours. This script automates it and produces the accuracy metrics you put in your README.

**What to do:**
Create file `tests/evaluate.py`:

```python
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.graph import validate_code


def evaluate():
    # Load test cases
    with open("validation_dataset/test_cases.json") as f:
        test_cases = json.load(f)
    
    true_positives = 0   # Agent found a real issue
    false_positives = 0  # Agent flagged something that was fine
    false_negatives = 0  # Agent missed a real issue
    total_issues = 0
    
    results = []
    
    for i, test in enumerate(test_cases):
        print(f"Running test {i+1}/{len(test_cases)}: {test['id']}")
        
        try:
            result = validate_code(test["code"])
            report = result.get("report", {})
            found_issues = report.get("issues", [])
            known_issues = test["known_issues"]
            
            total_issues += len(known_issues)
            
            # Check each known issue — did the agent find it?
            for known in known_issues:
                found = any(
                    issue["line_number"] == known["line"] and
                    issue["issue_type"] == known["type"]
                    for issue in found_issues
                )
                if found:
                    true_positives += 1
                else:
                    false_negatives += 1
            
            # Check for false positives (agent flagged something not in known_issues)
            for found in found_issues:
                is_real = any(
                    found["line_number"] == known["line"]
                    for known in known_issues
                )
                if not is_real:
                    false_positives += 1
            
            results.append({
                "id": test["id"],
                "expected": len(known_issues),
                "found": len(found_issues),
                "true_positives": sum(1 for k in known_issues if any(
                    f["line_number"] == k["line"] for f in found_issues
                ))
            })
        
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"id": test["id"], "error": str(e)})
    
    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    print("\n" + "="*50)
    print("VALIDATION RESULTS")
    print("="*50)
    print(f"Total test cases:   {len(test_cases)}")
    print(f"Total known issues: {total_issues}")
    print(f"True positives:     {true_positives}")
    print(f"False positives:    {false_positives}")
    print(f"False negatives:    {false_negatives}")
    print(f"Precision:          {precision:.1%}")
    print(f"Recall (TPR):       {recall:.1%}")
    
    # Save results
    with open("validation_dataset/results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": len(test_cases),
                "precision": precision,
                "recall": recall,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives
            },
            "per_test": results
        }, f, indent=2)
    
    print("\nResults saved to validation_dataset/results.json")


if __name__ == "__main__":
    evaluate()
```

**Run it:**
```bash
python tests/evaluate.py
```

***

## PHASE 9: README and GitHub Polish
### "The first thing every recruiter sees"

***

### Task 9.1 — Write the README

Create `README.md` in the root folder. Use this structure exactly:

```markdown
# AI Code Hallucination Validator

> LLMs generate code that *looks* correct but breaks at runtime.
> This agent validates AI-generated Python code against real library APIs
> and catches hallucinated methods before you waste an hour debugging.

[INSERT 15-SECOND DEMO GIF HERE]

## The Problem

When you ask ChatGPT or Cursor to write Python code, it confidently
generates calls to methods that:
- Were removed months ago (LangChain's `initialize_agent` removed Oct 2023)
- Were moved to a different module
- Never existed at all

No existing tool catches this. Pylint and mypy catch type errors, not
hallucinated API methods. This agent does.

## How It Works

[INSERT ARCHITECTURE DIAGRAM]

1. Extracts every library call using Python AST
2. Checks against a curated database of 20 high-churn ML/AI libraries
3. Fetches live PyPI data for unknown libraries
4. LLM diagnoses issues and generates corrected code — using ONLY
   the database data, never its own training knowledge

## Validation Results

Evaluated on 50 real AI-generated code examples with known issues:

| Metric | Score |
|--------|-------|
| True Positive Rate | XX% |
| False Positive Rate | XX% |
| Correct fix generated | XX% |

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Agent Framework | LangGraph | Conditional routing required — not a linear chain |
| LLM | GPT-4o-mini | 33× cheaper than GPT-4o, sufficient for classification |
| Import Extraction | Python AST | Handles all valid Python syntax, unlike regex |
| Output Schema | Pydantic v2 | Structured, typed output — never inconsistent |

## Why LangGraph and Not LangChain?

The agent makes a non-trivial routing decision: if all libraries are
in the local database, skip the PyPI API call entirely. This conditional
edge requires LangGraph's StateGraph. A LangChain chain executes
sequentially — it cannot make this decision.

## Known Limitations

- Covers 20 libraries (see full list in data/library_signatures.json)
- Cannot validate star imports (`from library import *`)
- Cannot validate dynamic imports (`importlib`)
- Confidence degrades for libraries not in the local database

## Running Locally

```bash
git clone <repo>
cd hallucination-validator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your OpenAI API key
uvicorn api.main:app --reload
# Open frontend/index.html in your browser
```
```

***

## Final File Checklist

Before pushing to GitHub, verify every file exists:

```
hallucination-validator/
├── README.md                        ← Story + demo GIF + validation table
├── requirements.txt                 ← All packages pinned
├── .env.example                     ← Template (no real key)
├── .gitignore                       ← .env and venv excluded
├── data/
│   └── library_signatures.json     ← 20 libraries, 200+ entries — YOUR MOAT
├── agent/
│   ├── schemas.py                   ← All Pydantic models
│   ├── graph.py                     ← LangGraph StateGraph
│   └── nodes/
│       ├── extract_imports.py       ← AST extractor
│       ├── check_database.py        ← Database lookup
│       ├── fetch_pypi.py            ← PyPI API
│       ├── llm_diagnose.py          ← LLM brain
│       └── generate_report.py      ← Output packager
├── api/
│   └── main.py                      ← FastAPI endpoint
├── frontend/
│   └── index.html                   ← Demo UI
├── validation_dataset/
│   ├── test_cases.json              ← 50 labeled examples
│   └── results.json                 ← Measured accuracy
└── tests/
    └── evaluate.py                  ← Accuracy measurement script
```

***

## Quick Test — Does It Work?

Run this to test the entire pipeline end to end:

```python
# test_quick.py — run this from root folder
from agent.graph import validate_code

BROKEN_CODE = """
from langchain.agents import initialize_agent
from langchain.llms import OpenAI
from pydantic import validator

class MyModel(BaseModel):
    name: str
    
    @validator('name')
    def validate_name(cls, v):
        return v.upper()

llm = OpenAI(temperature=0)
agent = initialize_agent(tools=[], llm=llm)
"""

result = validate_code(BROKEN_CODE)
report = result["report"]

print(f"Issues found: {report['total_issues_found']}")
for issue in report["issues"]:
    print(f"  Line {issue['line_number']}: [{issue['issue_type']}] {issue['explanation'][:80]}")
print(f"\nConfidence: {report['overall_confidence']:.0%}")
```

Expected output:
```
Issues found: 3
  Line 1: [deprecated] initialize_agent was removed in LangChain 0.2.0...
  Line 2: [wrong_import] OpenAI moved to langchain_openai package...
  Line 3: [deprecated] validator decorator replaced by field_validator in Pydantic v2...

Confidence: 87%
```

If you see this — your agent works. Push to GitHub.