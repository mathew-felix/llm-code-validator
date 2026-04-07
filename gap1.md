# Gap Completion Plan
### llm-code-validator | Current State: 50% precision, no README, no demo

***

## Honest Gap Summary

| Item | Status | Urgency |
|------|--------|---------|
| Precision (50%) → target 75%+ | ❌ Broken | 🔴 Critical — blocks GitHub push |
| README | ❌ Does not exist | 🔴 Critical — blocks GitHub push |
| Known Limitations section | ❌ Does not exist | 🔴 Critical |
| Demo GIF | ❌ Not recorded | 🟡 Important |
| requirements.txt pinned | ❓ Unconfirmed | 🟡 Important |
| .env in .gitignore | ❓ Unconfirmed | 🟡 Important |
| "Why LangGraph" written | ❌ Not written | 🟡 Important |
| Fresh clone test | ❌ Not done | 🟡 Important |
| Architecture diagram | ❌ Not made | 🟢 Nice to have |

***

***

# PHASE 1 — Fix the Precision Problem
### Target: 50% → 75%+ | Time: 1 full day

This is the only thing that matters before anything else.
A 50% precision number in your README tells hiring managers the tool
is wrong half the time it raises a flag. That is not publishable.
You must understand WHY it is failing before you write a single word of README.

***

## Task 1.1 — Run the Evaluator in Verbose Mode

**What this task is:**
Run your existing evaluate.py but capture every individual test result —
not just the aggregate score. You need to see each test case, what the
agent said, and whether it was right or wrong.

**Why this task is needed:**
You cannot fix a 50% precision problem without knowing which test cases
are failing and what pattern connects them. Right now you have a score
but no diagnosis. This task gives you the diagnosis.

**How it helps the problem:**
Once you see the failures grouped by pattern, you will find that 80% of
failures come from 1-2 root causes. Fix those root causes and precision
jumps significantly with minimal code change.

**What to do:**

If your evaluate.py does not already print per-case results, add this
temporarily to the evaluation loop:

```python
for case in test_cases:
    result = run_agent(case["code"])
    detected = extract_detected_methods(result)
    expected = extract_expected_methods(case["known_issues"])

    true_positives = detected & expected
    false_positives = detected - expected
    false_negatives = expected - detected

    if false_positives or false_negatives:
        print(f"\n--- FAIL: {case['id']} ---")
        print(f"  Description: {case['description']}")
        print(f"  False Positives (flagged but wrong): {false_positives}")
        print(f"  False Negatives (missed): {false_negatives}")
```

Run it. Save the output to a file:
```bash
python tests/evaluate.py > evaluation_results.txt 2>&1
```

Read every single failure line by line.

***

## Task 1.2 — Identify the Failure Pattern

**What this task is:**
Group all failures into categories. Every failure belongs to one of these
known categories. Find which ones your agent is hitting.

**Why this task is needed:**
Without categorization you will fix the wrong thing. Each category has a
different fix — fixing the wrong layer wastes a full day.

**How it helps the problem:**
Knowing the category tells you exactly which file to edit:
AST failures → fix extract_imports.py
Database failures → fix library_signatures.json entries
Prompt failures → fix llm_diagnose.py

**The 5 failure categories to look for:**

**Category A — Aliased Import Blindness**
Symptom: Test uses `import numpy as np` then calls `np.bool`
What agent sees: import of `numpy`, but the method call `np.bool` uses alias `np`
Agent cannot connect `np` back to `numpy` in the method check
Result: False Negative (missed the issue)

How to spot it in your output:
Look for test cases where the library is imported with `as` keyword
and the agent reports 0 issues found

**Category B — LLM Over-Flagging**
Symptom: Agent flags a method that actually exists and works fine
Result: False Positive (flagged something correct as broken)

How to spot it:
Look for false positives on methods that are NOT in your database
The LLM is using its own knowledge to hallucinate issues — the exact
problem your tool is meant to prevent, now happening inside your tool

**Category C — Database Entry Wrong**
Symptom: A method IS in your database but the entry has the wrong
library name, wrong method name, or wrong version info
Result: Either False Positive or False Negative depending on the error

How to spot it:
Find a false positive on a method that IS in your database
Check the exact JSON entry — likely a typo or wrong key name

**Category D — Method-Level vs Import-Level**
Symptom: Test case has `model.fit_transform()` (method call, not import)
Your AST extractor only pulls `import X` and `from X import Y`
It does NOT extract method calls on objects
Result: False Negative (missed a hallucinated method call)

How to spot it:
Look for test cases where the broken thing is a method call
(e.g., `df.append()`, `session.query()`, `pinecone.init()`)
not an import statement

**Category E — Version in Test Doesn't Match Database**
Symptom: Test case assumes library version X but database entry
is written for library version Y
Result: False Positive or False Negative depending on the mismatch

***

## Task 1.3 — Fix Category A (Aliased Imports)

**What this task is:**
Update extract_imports.py to track import aliases and resolve them
when checking method calls.

**Why this task is needed:**
Aliased imports are extremely common in real Python code.
`import numpy as np`, `import pandas as pd`, `import torch as th`
If your AST cannot resolve aliases, it misses a huge category of failures.

**How it helps the problem:**
Fixing this one issue likely accounts for 15-25% of your false negatives.
Precision and recall both jump.

**What to add to extract_imports.py:**

```python
import ast

def extract_imports_node(state):
    code = state["code"]
    tree = ast.parse(code)

    imports = []
    alias_map = {}  # maps alias → real library name

    for node in ast.walk(tree):
        # Handle: import numpy as np
        if isinstance(node, ast.Import):
            for alias in node.names:
                real_name = alias.name
                used_name = alias.asname if alias.asname else alias.name
                alias_map[used_name] = real_name
                imports.append({
                    "library": real_name,
                    "alias": alias.asname,
                    "type": "import"
                })

        # Handle: from pandas import DataFrame
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "library": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "type": "from_import"
                })

    # Extract method/attribute calls and resolve aliases
    method_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                caller = node.value.id
                method = node.attr
                real_library = alias_map.get(caller, caller)
                method_calls.append({
                    "library": real_library,
                    "method": method,
                    "alias_used": caller if caller != real_library else None
                })

    return {
        **state,
        "imports": imports,
        "method_calls": method_calls,
        "alias_map": alias_map
    }
```

Also update check_database.py to check BOTH imports AND method_calls
against the database — not just imports.

***

## Task 1.4 — Fix Category B (LLM Over-Flagging)

**What this task is:**
Tighten the LLM diagnosis prompt so the LLM ONLY reports issues
that are confirmed by the database or PyPI data — not from its own memory.

**Why this task is needed:**
Your tool's entire purpose is to catch LLM hallucinations.
If your own LLM node is hallucinating issues, you have built
a hypocrite into the system.

**How it helps the problem:**
Eliminating false positives directly raises precision.
Every false positive you eliminate moves the precision number up.

**What to change in llm_diagnose.py:**

Find the system prompt. Replace the current instructions with this
tighter version:

```python
DIAGNOSIS_SYSTEM_PROMPT = """You are a code validation engine.
Your ONLY job is to identify issues in the provided Python code
based EXCLUSIVELY on the evidence given to you.

You have two sources of evidence:
1. database_matches: Known breaking changes from our curated database
2. pypi_data: Live package metadata from PyPI (if provided)

STRICT RULES:
- You may ONLY flag an issue if it appears in database_matches or pypi_data
- You may NOT use your own training knowledge about APIs
- You may NOT flag something as "potentially deprecated" or "might be wrong"
- If you are not certain based on the evidence given, do NOT flag it
- Every issue you report MUST cite which database entry or PyPI field
  proves the issue exists

If the evidence shows no issues, return an empty issues list.
It is better to miss an issue than to invent one.

Response format: JSON matching the ValidationReport schema exactly.
"""
```

The key line is: **"It is better to miss an issue than to invent one."**
This single instruction trades some recall for much higher precision —
which is the right tradeoff for a tool people will actually trust.

***

## Task 1.5 — Rerun and Record the New Numbers

After fixing Tasks 1.3 and 1.4:

```bash
python tests/evaluate.py
```

Record the new precision and recall numbers. These go in your README.

**Acceptable outcome:** 72–85% precision, 60–75% recall
**Good outcome:** 80%+ precision, 70%+ recall
**If still below 70% precision:** Run verbose mode again, find the
remaining category, fix it before moving on.

The real number — whatever it is after honest fixing — goes in the README.
Do not round up. Do not cherry-pick libraries where it gets 100%.
The overall number on all 50 cases is the number that gets published.

***

***

# PHASE 2 — Write the README
### Time: 1 full day | Blocks: Everything visible on GitHub

The README is the project. Everything else is implementation details.
A recruiter will spend 90 seconds on your repo. This document controls
what they think of you in those 90 seconds.

***

## Task 2.1 — Record the Demo GIF (Do This First, 30 Minutes)

**What this task is:**
A 15-second screen recording showing the tool working end to end.

**Why this task is needed:**
Humans do not read READMEs. They look at the GIF.
If there is no GIF, most people close the tab.
The GIF is the proof that it works without anyone having to clone it.

**How it helps the problem:**
A working GIF eliminates the single biggest objection: "does this actually work?"

**What to record:**
1. Start: empty text area in the frontend
2. Paste this exact code (copy it, it is designed to trigger 2 clear issues):
```python
import pinecone
from langchain.chat_models import ChatOpenAI
import pandas as pd

pinecone.init(api_key="sk-...", environment="us-east1-gcp")
index = pinecone.Index("my-index")

llm = ChatOpenAI(model_name="gpt-4")
df = pd.DataFrame({"a": [1, 2, 3]})
df2 = df.append({"a": 4}, ignore_index=True)
```
3. Click Validate
4. Show 3 issues appearing as colored cards
5. Stop recording

**Tools to use:**
- Mac: QuickTime → File → New Screen Recording, then convert to GIF with Gifski
- Windows: ShareX (free) records directly to GIF
- Any OS: Loom (records to MP4, then use ezgif.com to convert)

**Save as:** `assets/demo.gif` in your repo

***

## Task 2.2 — Draw the Architecture Diagram (30 Minutes)

**What this task is:**
A simple diagram showing the LangGraph flow from input to output.

**Why this task is needed:**
Engineers want to see you understand your own system at a glance.
A diagram communicates the conditional routing faster than 3 paragraphs.

**How to make it:**
Go to excalidraw.com (free, no account needed)

Draw these boxes connected by arrows:
```
[User pastes code]
        ↓
[FastAPI /validate endpoint]
        ↓
[AST Parser — extract_imports node]
        ↓
[Database Lookup — check_database node]
        ↓
    ← Known? →
   YES         NO
    ↓           ↓
    |    [PyPI Fetch node]
    |           ↓
    └───────────┘
        ↓
[LLM Diagnosis — gpt-4o-mini, temp=0.1]
        ↓
[Report Generator — Pydantic output]
        ↓
[Frontend renders issue cards]
```

Label the conditional branch: "Is library in our 20-library database?"
Export as PNG. Save as `assets/architecture.png`

***

## Task 2.3 — Write the README Sections in This Exact Order

**What this task is:**
Write the complete README.md file. Sections listed in the exact order
a reader encounters them.

**Why this task is needed:**
Without a README, the project does not professionally exist.
A GitHub repo with no README is a folder of files. It communicates nothing.

**How it helps the problem:**
The README is what gets shared in Slack when a recruiter finds your repo.
It is what gets screenshotted and sent to a hiring manager.
It is what you pull up on your laptop in an interview.

**Write the README in this exact section order:**

***

### Section 1: Title + One-Sentence Description

```markdown
# llm-code-validator

Validates AI-generated Python code against real library APIs —
catches hallucinated methods and deprecated imports before they waste your debugging time.
```

Nothing more. One sentence. No paragraph.

***

### Section 2: Demo GIF

```markdown
![Demo](assets/demo.gif)
```

Put this immediately after the title. Before any other text.
The GIF is the first thing they see after the title.

***

### Section 3: The Problem (3 sentences maximum)

```markdown
## The Problem

LLMs generate Python code using APIs that no longer exist.
`pinecone.init()` was removed in v3. `langchain.chat_models` was restructured.
`pandas.DataFrame.append()` was dropped in 2.0. Models trained before these changes
don't know — and they generate broken code with complete confidence.
```

Three sentences. Tell the story. Name specific real examples.

***

### Section 4: How It Works

```markdown
## How It Works

![Architecture](assets/architecture.png)

1. Paste AI-generated Python code into the web UI
2. The AST parser extracts all imports and method calls without executing the code
3. Imports are cross-referenced against a curated database of 75+ known breaking changes
4. If a library is outside the database, live PyPI metadata is fetched as fallback
5. A low-temperature GPT-4o-mini prompt diagnoses issues using only the database evidence — not its own memory
6. Issues are returned as structured JSON and rendered as fix cards in the UI
```

***

### Section 5: Why LangGraph (Write This From Memory)

```markdown
## Why LangGraph, Not a LangChain Chain

The validation workflow requires a **conditional branch**: if all imported libraries
exist in the local database, the PyPI network call is skipped entirely. If any library
is unknown, the PyPI fetch node runs before the LLM diagnosis.

A LangChain chain is sequential — every step runs every time, in order.
LangGraph's `StateGraph` with `add_conditional_edges` lets the graph inspect
the current state and route to a different node based on a condition.
This makes the agent faster (no unnecessary API calls) and more deterministic
(the routing logic is explicit code, not LLM reasoning).
```

This is the paragraph you will speak aloud in interviews.
Write it in your own words. The version above is a starting point — change
the phrasing so it sounds like you.

***

### Section 6: Validation Results

```markdown
## Validation Results

Evaluated against 50 real broken Python scripts sourced from Stack Overflow questions,
GitHub issues, and LlamaIndex/LangChain migration guides. Test cases were collected
externally — not written to match the database.

| Metric | Result |
|--------|--------|
| Test cases | 50 (external sources) |
| Libraries covered | 20 |
| Database entries | 75+ |
| Precision | XX% |
| Recall | XX% |

_Fill XX% with the real numbers from Phase 1._
```

***

### Section 7: Known Limitations

```markdown
## Known Limitations

These are the documented cases where the validator does not work:

- **Aliased imports**: `import numpy as np` followed by `np.bool` — the alias
  resolution is partially supported but not complete for deeply chained calls
- **Star imports**: `from langchain import *` cannot be analyzed statically
- **Dynamic imports**: `importlib.import_module('pandas')` is not detected
- **Libraries outside the 20**: Falls back to PyPI metadata, which confirms
  the package exists but cannot validate specific method signatures
- **Version-specific code**: If the code explicitly pins a version that predates
  a breaking change, the validator may flag correct code as deprecated
```

Write the real limitations from your Phase 1 failure analysis.
The list above is a starting point — add or remove based on what
your verbose evaluator output actually showed.

***

### Section 8: Tech Stack

```markdown
## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Agent framework | LangGraph 0.2.x | Conditional routing between nodes |
| LLM | GPT-4o-mini (temp=0.1) | Low temperature for deterministic diagnosis |
| Import parsing | Python `ast` module | Static analysis — no code execution |
| API validation | PyPI JSON API | Free, no auth, live package metadata |
| Backend | FastAPI | Async, fast, Pydantic-native |
| Output schema | Pydantic v2 | Strict typing guarantees on LLM output |
| Frontend | Vanilla HTML/JS | Zero build-tool dependencies |
```

***

### Section 9: Running Locally

```markdown
## Running Locally

```bash
git clone https://github.com/[username]/llm-code-validator
cd llm-code-validator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your OPENAI_API_KEY
uvicorn api.main:app --reload
```

Open `frontend/index.html` in your browser.
```

Five commands. No more. No explanation of what each one does.
If it needs more explanation than this, the setup is too complicated.

***

***

# PHASE 3 — Final Checklist Before Push
### Time: 2-3 hours | Do not skip any item

***

## Task 3.1 — Pin All Dependencies

```bash
pip freeze > requirements.txt
```

Open requirements.txt and verify these exact packages are present
with pinned versions (== not >=):

```
langgraph==0.2.28
langchain==0.3.7
openai==1.54.0
pydantic==2.9.2
fastapi==0.115.4
uvicorn==0.32.0
httpx==0.27.2
python-dotenv==1.0.1
```

If any are missing, add them manually. If the versions differ slightly
from the above, keep your installed versions — just make sure they are pinned.

***

## Task 3.2 — Verify .gitignore

**What to check:**
Open .gitignore and confirm these lines exist:

```
.env
venv/
__pycache__/
*.pyc
.DS_Store
evaluation_results.txt
```

Then run:
```bash
git status
```

Confirm `.env` does NOT appear as an untracked or staged file.
If it does, add it to .gitignore immediately and run:
```bash
git rm --cached .env
```

***

## Task 3.3 — Fresh Clone Test

**What this task is:**
Clone your own repo into a new folder and follow your own README
to get it running from scratch.

**Why this task is needed:**
Your current setup has the venv, the .env, and all the context
in your head. A fresh clone has none of that. This test finds
every step you forgot to document and every dependency you forgot to pin.

**How to do it:**
```bash
cd /tmp
git clone https://github.com/[username]/llm-code-validator fresh-test
cd fresh-test
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your API key to .env
uvicorn api.main:app --reload
```

Open the frontend. Paste code. Click validate. Confirm it works.
If anything breaks during this process — fix it in the original repo.

***

## Task 3.4 — Final File Audit

Confirm every file exists:

```
hallucination-validator/
├── README.md                          ← written in Phase 2
├── requirements.txt                   ← pinned versions
├── .env.example                       ← with placeholder values, not real keys
├── .gitignore                         ← .env excluded
├── assets/
│   ├── demo.gif                       ← recorded in Task 2.1
│   └── architecture.png               ← drawn in Task 2.2
├── data/
│   └── library_signatures.json        ← 20 libraries, 75+ entries
├── agent/
│   ├── schemas.py
│   ├── graph.py
│   └── nodes/
│       ├── extract_imports.py         ← updated with alias resolution
│       ├── check_database.py
│       ├── fetch_pypi.py
│       ├── llm_diagnose.py            ← updated with tighter prompt
│       └── generate_report.py
├── api/
│   └── main.py
├── frontend/
│   └── index.html
└── validation_dataset/
    ├── test_cases.json                ← 50 external cases
    └── results.json                   ← output from evaluate.py after Phase 1 fix
```

***

## Task 3.5 — Push and Verify on GitHub

```bash
git add .
git commit -m "feat: complete validation suite, README, and precision fixes"
git push origin main
```

After pushing:
1. Open your GitHub repo in a browser
2. Confirm the README renders correctly with the GIF playing
3. Confirm the architecture diagram loads
4. Confirm no .env file appears in the file list
5. Click the demo.gif — confirm it plays in the GitHub viewer

***

***

# Day-by-Day Schedule

| Day | Focus | Morning | Afternoon | End of Day Target |
|-----|-------|---------|-----------|-------------------|
| **Day 1** | Fix precision | Run evaluator verbose, diagnose failure patterns | Fix alias resolution + tighten LLM prompt, rerun | Precision at 75%+ with real numbers |
| **Day 2** | README | Record demo GIF + draw architecture diagram | Write all 9 README sections | Complete README.md committed |
| **Day 3** | Push | Pin deps, .gitignore check, fresh clone test | Final file audit, push to GitHub | Live on GitHub, all checks green |

**3 days. Then it is done.**

***

## What You Will Have After 3 Days

| Evidence | What It Proves |
|----------|----------------|
| 75%+ precision on 50 external test cases | The tool works on data you did not control |
| Documented failure modes | You know the boundaries of your own tool |
| Demo GIF showing it working | It works — provable in 15 seconds without cloning |
| "Why LangGraph" paragraph | You understand the architecture, not just the syntax |
| Fresh clone test passed | Any engineer can run it from your README |
| Real validation results table | You report honest numbers, not cherry-picked ones |

This is what a finished project looks like.
Not perfect. Not complete coverage of every library.
But honest, well-documented, and provably working on real external data.
That is the bar. 3 days gets you there.