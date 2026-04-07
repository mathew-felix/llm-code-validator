# What Is Missing — Completion Plan
### llm-code-validator | Starting point: 8 libraries, 5 tests, 100% fake precision

---

## Honest Gap Analysis

| Component | Plan Target | Current State | Gap |
|-----------|-------------|---------------|-----|
| Library database | 20 libraries | 8 libraries | 12 missing |
| Test cases | 50 real external examples | 5 self-written examples | 45 missing |
| Precision measurement | Real number from real data | 100% on self-made tests (meaningless) | Needs rerun |
| README | Full story + validation table | Does not exist | 100% missing |
| Known limitations section | Documented honestly | Does not exist | 100% missing |
| "Why LangGraph" explanation | Written and owned | Not written | Missing |
| Demo GIF | 15-second recorded demo | Not recorded | Missing |

---

## PHASE A: Complete the Database (3 Days)
### The only thing that actually matters this week

The 8 libraries you have are the obvious ones. Anyone building a tutorial
project would have these same 8. The next 12 are where your moat actually starts.

---

### Task A.1 — LlamaIndex (2 hours)

**Why this library matters:**
LlamaIndex went through a complete package rewrite in version 0.10 (Feb 2024).
The entire import structure changed. Every piece of AI-generated code using
LlamaIndex is almost certainly using the old API. This is one of the highest
false-confidence failures in the space.

**Where to find the breaking changes:**
https://github.com/run-llama/llama_index/releases/tag/v0.10.0
Look for: "Migration Guide" section in the 0.10.0 release notes

**What to add to library_signatures.json:**
```json
"llama_index": {
  "current_version": "0.10.x",
  "last_updated": "2026-04-07",
  "methods": {
    "GPTSimpleVectorIndex": {
      "exists": false,
      "removed_in": "0.10.0",
      "removed_date": "2024-02-15",
      "reason": "Complete package restructure — all index classes moved and renamed",
      "old_import": "from llama_index import GPTSimpleVectorIndex",
      "replacement": "from llama_index.core import VectorStoreIndex",
      "replacement_example": "from llama_index.core import VectorStoreIndex, SimpleDirectoryReader\ndocs = SimpleDirectoryReader('data').load_data()\nindex = VectorStoreIndex.from_documents(docs)"
    },
    "ServiceContext": {
      "exists": false,
      "removed_in": "0.10.0",
      "reason": "Replaced by Settings global configuration object",
      "old_import": "from llama_index import ServiceContext",
      "replacement": "from llama_index.core import Settings",
      "replacement_example": "from llama_index.core import Settings\nfrom llama_index.llms.openai import OpenAI\nSettings.llm = OpenAI(model='gpt-4o-mini')"
    },
    "LLMPredictor": {
      "exists": false,
      "removed_in": "0.10.0",
      "reason": "Removed entirely — use Settings.llm directly",
      "old_import": "from llama_index import LLMPredictor",
      "replacement": "from llama_index.core import Settings"
    },
    "SimpleDirectoryReader": {
      "exists": true,
      "module_current": "llama_index.core",
      "module_old": "llama_index",
      "changed_in": "0.10.0",
      "old_import": "from llama_index import SimpleDirectoryReader",
      "new_import": "from llama_index.core import SimpleDirectoryReader"
    }
  }
}
```

**Verify each entry:** Search GitHub Issues on run-llama/llama_index for
"ImportError" or "cannot import" to confirm these are real user failures.

---

### Task A.2 — CrewAI (1.5 hours)

**Why this library matters:**
CrewAI is one of the fastest-changing libraries in the AI agent space.
It shipped in late 2023 and has had breaking API changes almost every month.
LLMs trained before mid-2024 generate completely wrong CrewAI syntax.

**Where to find breaking changes:**
https://github.com/crewAIInc/crewAI/releases
Focus on releases from v0.28.0 onward — this is where the major restructuring happened.

**What to add:**
```json
"crewai": {
  "current_version": "0.80.x",
  "last_updated": "2026-04-07",
  "methods": {
    "Task.output": {
      "exists": false,
      "removed_in": "0.28.0",
      "reason": "Task output handling restructured — use TaskOutput object",
      "replacement": "Access via crew.kickoff().raw or crew.kickoff().pydantic"
    },
    "Process.sequential": {
      "exists": true,
      "note": "Still exists but import path changed in 0.30.0",
      "old_import": "from crewai import Process",
      "new_import": "from crewai import Process",
      "note": "Import unchanged but process behavior changed — tasks no longer auto-share context"
    },
    "Agent": {
      "exists": true,
      "note": "allow_delegation default changed from True to False in 0.51.0",
      "common_mistake": "Old code assumes agents can delegate by default — must now pass allow_delegation=True explicitly",
      "old_behavior": "Agent(role='...', goal='...', backstory='...')  # delegation was True",
      "new_behavior": "Agent(role='...', goal='...', backstory='...', allow_delegation=True)"
    }
  }
}
```

---

### Task A.3 — NumPy 2.0 (2 hours)

**Why this library matters:**
NumPy 2.0 (June 2024) removed dozens of deprecated functions that had existed
since NumPy 1.x. Every LLM trained before mid-2024 generates NumPy 1.x code.
This affects nearly every data science codebase.

**Where to find breaking changes:**
https://numpy.org/doc/stable/release/2.0.0-notes.html
Section: "Expired deprecations" — this is the complete list of removals.

**What to add (highest priority entries):**
```json
"numpy": {
  "current_version": "2.0.x",
  "last_updated": "2026-04-07",
  "methods": {
    "np.bool": {
      "exists": false,
      "removed_in": "2.0.0",
      "removed_date": "2024-06-16",
      "reason": "Alias for Python built-in bool was removed",
      "old_usage": "np.bool",
      "replacement": "bool or np.bool_",
      "replacement_example": "arr = np.array([True, False], dtype=bool)"
    },
    "np.int": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Alias for Python built-in int was removed",
      "old_usage": "np.int",
      "replacement": "int or np.int_"
    },
    "np.float": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Alias for Python built-in float was removed",
      "old_usage": "np.float",
      "replacement": "float or np.float64"
    },
    "np.complex": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Alias for Python built-in complex was removed",
      "old_usage": "np.complex",
      "replacement": "complex or np.complex128"
    },
    "np.object": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Alias for Python built-in object was removed",
      "old_usage": "np.object",
      "replacement": "object or np.object_"
    },
    "np.string_": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Renamed to np.bytes_",
      "replacement": "np.bytes_"
    }
  }
}
```

---

### Task A.4 — SQLAlchemy 2.0 (2 hours)

**Why this library matters:**
SQLAlchemy 2.0 (Jan 2023) was a complete ORM rewrite. The session API,
query API, and execution model all changed. This is one of the most
commonly broken libraries in full-stack Python projects.

**Where to find breaking changes:**
https://docs.sqlalchemy.org/en/20/changelog/migration_20.html

**What to add:**
```json
"sqlalchemy": {
  "current_version": "2.0.x",
  "last_updated": "2026-04-07",
  "methods": {
    "Session.execute": {
      "exists": true,
      "note": "Signature changed — no longer accepts legacy Query objects",
      "old_usage": "session.execute(MyModel.__table__.select())",
      "new_usage": "session.execute(select(MyModel))",
      "replacement_example": "from sqlalchemy import select\nresult = session.execute(select(MyModel).where(MyModel.id == 1))"
    },
    "Query": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Legacy Query API removed — replaced by select() construct",
      "old_usage": "session.query(MyModel).filter(MyModel.id == 1).first()",
      "replacement": "session.execute(select(MyModel).where(MyModel.id == 1)).scalar_one_or_none()",
      "replacement_example": "from sqlalchemy import select\nstmt = select(MyModel).where(MyModel.id == 1)\nresult = session.execute(stmt).scalar_one_or_none()"
    },
    "Engine.execute": {
      "exists": false,
      "removed_in": "2.0.0",
      "reason": "Removed connectionless execution — use connection context manager",
      "old_usage": "engine.execute('SELECT * FROM table')",
      "replacement": "with engine.connect() as conn:\n    result = conn.execute(text('SELECT * FROM table'))"
    }
  }
}
```

---

### Task A.5 — Anthropic SDK (1 hour)

**Why this library matters:**
The Anthropic Python SDK changed its message API structure significantly.
Claude is now a primary LLM choice for many developers — broken Anthropic
SDK code is increasingly common in AI-generated scripts.

**Where to find breaking changes:**
https://github.com/anthropics/anthropic-sdk-python/releases

**What to add:**
```json
"anthropic": {
  "current_version": "0.40.x",
  "last_updated": "2026-04-07",
  "methods": {
    "anthropic.Anthropic.completions.create": {
      "exists": false,
      "removed_in": "0.20.0",
      "reason": "Completions API removed — use messages.create",
      "old_usage": "client.completions.create(model='claude-2', prompt=prompt, max_tokens=1000)",
      "replacement": "client.messages.create(model='claude-3-5-sonnet-20241022', max_tokens=1000, messages=[{'role': 'user', 'content': prompt}])"
    },
    "HUMAN_PROMPT": {
      "exists": false,
      "removed_in": "0.20.0",
      "reason": "Special prompt tokens removed with completions API",
      "old_usage": "f'{HUMAN_PROMPT} Hello {AI_PROMPT}'",
      "replacement": "Use messages list format instead"
    }
  }
}
```

---

### Task A.6 — LangGraph Itself (1.5 hours)

**Why this library matters:**
This is the framework your project IS BUILT ON. LangGraph changes frequently.
LLMs generate old LangGraph syntax constantly — especially the pre-0.2 API
where graph compilation and state management worked differently.
Adding this to your database is also a powerful story: "I even validated the
framework I'm using."

**Where to find breaking changes:**
https://github.com/langchain-ai/langgraph/releases
Focus on 0.1.x → 0.2.x migration.

**What to add:**
```json
"langgraph": {
  "current_version": "0.2.x",
  "last_updated": "2026-04-07",
  "methods": {
    "MessageGraph": {
      "exists": false,
      "removed_in": "0.2.0",
      "reason": "Replaced by StateGraph with MessagesState",
      "old_import": "from langgraph.graph import MessageGraph",
      "replacement": "from langgraph.graph import StateGraph\nfrom langgraph.graph.message import MessagesState",
      "replacement_example": "graph = StateGraph(MessagesState)"
    },
    "StateGraph.compile": {
      "exists": true,
      "note": "Signature changed — checkpointer parameter renamed and restructured in 0.2.0",
      "old_usage": "graph.compile(checkpointer=MemorySaver())",
      "new_usage": "graph.compile(checkpointer=MemorySaver())",
      "note": "Syntax unchanged but MemorySaver import path changed",
      "old_import": "from langgraph.checkpoint import MemorySaver",
      "new_import": "from langgraph.checkpoint.memory import MemorySaver"
    },
    "END": {
      "exists": true,
      "module_current": "langgraph.graph",
      "note": "Still exists but must be imported — not a global constant",
      "common_mistake": "Using END without importing it",
      "correct_import": "from langgraph.graph import StateGraph, END"
    }
  }
}
```

---

### Task A.7 — Pinecone SDK v3 (1 hour)

**Where to find:** https://github.com/pinecone-io/pinecone-python-client/releases

```json
"pinecone": {
  "current_version": "3.x",
  "last_updated": "2026-04-07",
  "methods": {
    "pinecone.init": {
      "exists": false,
      "removed_in": "3.0.0",
      "reason": "Global init pattern removed — use Pinecone client class",
      "old_usage": "import pinecone\npinecone.init(api_key='...', environment='...')",
      "replacement": "from pinecone import Pinecone\npc = Pinecone(api_key='...')"
    },
    "pinecone.create_index": {
      "exists": false,
      "removed_in": "3.0.0",
      "reason": "Module-level functions removed — use client methods",
      "old_usage": "pinecone.create_index('index-name', dimension=1536)",
      "replacement": "pc.create_index(name='index-name', dimension=1536, spec=ServerlessSpec(cloud='aws', region='us-east-1'))"
    },
    "pinecone.Index": {
      "exists": false,
      "removed_in": "3.0.0",
      "reason": "Module-level class access removed",
      "old_usage": "index = pinecone.Index('index-name')",
      "replacement": "index = pc.Index('index-name')"
    }
  }
}
```

---

### Tasks A.8 through A.12 — Remaining Libraries

For each of these, follow the same process:
1. Go to GitHub releases page
2. Find breaking changes from 2023–2025
3. Add 3–8 entries per library
4. Verify each entry with a real Stack Overflow question or GitHub issue

**A.8 — ChromaDB**
URL: https://github.com/chroma-core/chroma/releases
Focus: Client API restructure in 0.4.x (Settings class removed, Client/HttpClient split)

**A.9 — Pandas 2.0 additions** (you have pandas but likely missing key entries)
URL: https://pandas.pydata.org/docs/whatsnew/v2.0.0.html
Focus: .append() removed, inplace parameter deprecated, CopyOnWrite behavior

**A.10 — TensorFlow/Keras 3.0**
URL: https://keras.io/guides/migrating_to_keras_3/
Focus: keras import restructure, model.fit signature changes

**A.11 — HuggingFace Transformers additions** (you have it but likely incomplete)
URL: https://github.com/huggingface/transformers/releases
Focus: Trainer API changes in 4.36+, pipeline() signature changes, tokenizer fast/slow

**A.12 — Motor / PyMongo async**
URL: https://pymongo.readthedocs.io/en/stable/changelog.html
Focus: async Motor vs sync PyMongo confusion — LLMs mix them constantly

---

## PHASE B: Build Real Test Cases (2 Days)
### Replacing 5 self-written tests with 50 real external examples

---

### Task B.1 — Understand What Makes a Good Test Case

A good test case has three properties:
1. **External origin** — you did not write it, someone else hit this error
2. **Verifiable** — there is a Stack Overflow answer, GitHub issue, or error message confirming it is wrong
3. **Labeled** — you know exactly which line fails and why

A bad test case is code you wrote to match your own database entries.
That is exactly what your 5 current tests are.

---

### Task B.2 — Source 1: Stack Overflow (Day 1, ~3 hours, target 20 examples)

**Search queries to use:**
```
site:stackoverflow.com [langchain] "ImportError" 2024
site:stackoverflow.com [langchain] "cannot import name" 2024
site:stackoverflow.com [openai] "has no attribute" 2024
site:stackoverflow.com [pydantic] "ValidationError" "v2" 2024
site:stackoverflow.com [llama-index] "ImportError" 2024
site:stackoverflow.com [pinecone] "AttributeError" 2024
site:stackoverflow.com [crewai] "ImportError" 2025
```

**For each result:**
- Copy the broken code from the question (not the answer)
- Copy the error message
- Record which library, which method, which line
- Add to test_cases.json with `"source": "stackoverflow.com/questions/[ID]"`

---

### Task B.3 — Source 2: Reddit (Day 1, ~2 hours, target 10 examples)

**Subreddits to search:**
- r/LocalLLaMA — search "hallucination code" or "wrong import"
- r/learnpython — search "AI generated" + error message
- r/LangChain — search "ImportError" or "AttributeError"
- r/MachineLearning — search "deprecated" + library name

For each post: copy the broken code, record the error, label the issue type.

---

### Task B.4 — Source 3: GitHub Issues (Day 1, ~2 hours, target 10 examples)

**Repositories to search:**
```
github.com/langchain-ai/langchain/issues?q=label:bug+ImportError
github.com/huggingface/transformers/issues?q=label:bug+deprecated
github.com/ultralytics/ultralytics/issues?q=ImportError (your thesis repo)
github.com/pinecone-io/pinecone-python-client/issues?q=AttributeError
```

For each issue: copy the user's broken code from the issue body (not the fix).

---

### Task B.5 — Source 4: Your Own Thesis Debugging (Day 1, ~1 hour, target 5 examples)

Go back through your thesis work. Every time you got an ImportError,
AttributeError, or wrong method call while building the Jetson pipeline —
that is a real test case. These are the most valuable because:
- You can tell the story in an interview
- They connect the project to your research background
- Nobody else has them

Write them down from memory. If you kept any logs or error messages, use those.

---

### Task B.6 — Source 5: Generate Intentionally Broken Code (Day 2, ~2 hours, target 10 examples)

**Method:** Ask an LLM with an old training cutoff to write code for tasks using
libraries that changed. Do not tell it about the changes. Collect the broken code it produces.

**Prompts to use:**
```
"Write a LangChain agent that uses memory and tools" → will generate old initialize_agent
"Write a script that uses LlamaIndex to query a PDF" → will generate old GPTSimpleVectorIndex
"Write a Pydantic model with validation" → will generate old @validator decorator
"Write a CrewAI agent team" → will generate old delegation syntax
"Initialize a Pinecone index and upsert vectors" → will generate old pinecone.init()
```

Collect the broken outputs. These are real hallucinations from a real LLM.
Label them. Add to test_cases.json.

---

### Task B.7 — Final Test Cases JSON Format

Each of the 50 entries must follow this exact structure:

```json
{
  "id": "test_021",
  "description": "LlamaIndex 0.10 migration — GPTSimpleVectorIndex removed",
  "difficulty": "medium",
  "code": "from llama_index import GPTSimpleVectorIndex, SimpleDirectoryReader\n\ndocs = SimpleDirectoryReader('data').load_data()\nindex = GPTSimpleVectorIndex.from_documents(docs)\nquery_engine = index.as_query_engine()\nresponse = query_engine.query('What is this document about?')",
  "known_issues": [
    {
      "line": 1,
      "type": "deprecated",
      "method": "GPTSimpleVectorIndex",
      "library": "llama_index",
      "description": "Removed in 0.10.0 — use VectorStoreIndex from llama_index.core"
    },
    {
      "line": 1,
      "type": "wrong_import",
      "method": "SimpleDirectoryReader",
      "library": "llama_index",
      "description": "Module path changed — now in llama_index.core"
    }
  ],
  "source": "stackoverflow.com/questions/[ID]",
  "verified": true,
  "notes": "Confirmed by 47 upvotes on SO answer pointing to migration guide"
}
```

---

## PHASE C: Rerun the Evaluator and Get Real Numbers (Half Day)

---

### Task C.1 — Run tests/evaluate.py on All 50 Cases

```bash
python tests/evaluate.py
```

Your precision will drop. Accept it. Record the real numbers.

**What real numbers look like for a good project:**
- Precision 78–88% → Good. Document which cases it misses and why.
- Precision below 70% → Database has gaps. Find which libraries are failing.
- Precision above 95% on 50 external cases → Genuinely impressive.

---

### Task C.2 — Document Where It Fails (This Is Your Limitations Section)

After running the evaluator, find every false positive and false negative.
Group them by failure type. You will likely see:

**Common failure patterns to look for:**
1. Aliased imports (`import numpy as np` — AST sees `np` not `numpy`)
2. Star imports (`from langchain import *`)
3. Libraries added after your database cutoff
4. Methods that exist in one version but not another (version-dependent)

Write these up honestly. This becomes your "Known Limitations" section.
This section, written with engineering precision, is worth more to a hiring
manager than a fake 100% precision score.

---

## PHASE D: README and GitHub Polish (1 Day)

---

### Task D.1 — Write the README

**Mandatory sections in this order:**

1. **One sentence what it does**
   > "Validates AI-generated Python code against real library APIs — catches hallucinated methods and deprecated calls before they waste your debugging time."

2. **Demo GIF** (record this with Loom or ScreenToGif — 15 seconds max)
   - Start: blank input box
   - Paste 10 lines of broken LangChain code
   - Click validate
   - Show 2 issues found with corrections
   - End. That is the entire demo.

3. **The Problem** (3 sentences max — quote Simon Willison)

4. **Architecture diagram** (hand-draw in Excalidraw, export as PNG)
   Show: input → AST → database → [conditional] → PyPI / LLM → report

5. **Validation Results table**
   | Metric | Result |
   |--------|--------|
   | Test cases | 50 real external examples |
   | True Positive Rate | XX% |
   | False Positive Rate | XX% |
   | Libraries covered | 20 |

6. **Tech Stack table with reasons**
   Include the "Why LangGraph not LangChain" row explicitly.

7. **Known Limitations** (from Task C.2)

8. **Running Locally** (5 commands, nothing more)

---

### Task D.2 — Write the "Why LangGraph" Explanation

This is the single most important paragraph in your README for technical
readers. Write it in your own words. It must explain:

- What the conditional edge is
- What decision it makes
- Why a LangChain chain cannot make that decision
- How LangGraph's StateGraph enables it

If you cannot write this from memory right now, sit with the graph.py file
until you can. This is the paragraph you will speak aloud in interviews.

---

### Task D.3 — Final GitHub Checklist

Before pushing:
- [ ] README has demo GIF at the top
- [ ] validation_dataset/results.json exists with real numbers
- [ ] library_signatures.json has 20 libraries
- [ ] validation_dataset/test_cases.json has 50 entries each with "source" field
- [ ] Known limitations section is honest and specific
- [ ] requirements.txt has pinned versions
- [ ] .env is in .gitignore (check this twice)
- [ ] No hardcoded API keys anywhere in code
- [ ] All 5 node files have 2-line docstrings
- [ ] README "Running Locally" section works on a fresh clone

---

## Day-by-Day Schedule

| Day | Morning (3–4 hrs) | Afternoon (3–4 hrs) | End of Day Target |
|-----|-------------------|---------------------|-------------------|
| **Day 1** | A.1 LlamaIndex + A.2 CrewAI | A.3 NumPy + A.4 SQLAlchemy | 4 new libraries added |
| **Day 2** | A.5 Anthropic + A.6 LangGraph | A.7 Pinecone + A.8 ChromaDB | 8 new libraries added |
| **Day 3** | A.9–A.12 remaining 4 libraries | Verify all 20 entries with real sources | All 20 libraries complete |
| **Day 4** | B.2 Stack Overflow — 20 cases | B.3 Reddit — 10 cases | 30 test cases collected |
| **Day 5** | B.4 GitHub Issues — 10 cases | B.5 Thesis examples + B.6 Generated examples | All 50 test cases done |
| **Day 6** | C.1 Run evaluator on all 50 | C.2 Analyze failures, write limitations | Real accuracy numbers in hand |
| **Day 7** | D.1 Write README + record demo GIF | D.2 Why LangGraph section + D.3 final checklist | Push to GitHub |

**Total: 7 more days of focused work.**

---

## What You Will Have After These 7 Days

| Item | Value to Hiring Manager |
|------|------------------------|
| 20-library database with verified entries | "They did the unglamorous work completely" |
| 50 external test cases with sources | "They validated against real-world data, not toy examples" |
| Honest precision/recall numbers | "They think like an engineer, not a demo builder" |
| Documented limitations | "They know what their tool can and cannot do" |
| "Why LangGraph" explanation | "They understand the framework choice, not just the syntax" |
| Demo GIF | "I can see it works in 15 seconds" |

This is the difference between a project you are embarrassed to show in an
interview and one you are proud to walk through line by line.

