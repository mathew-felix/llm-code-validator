# Demo

This demo shows the local check and safe-fix workflow on a small AI-stack snippet.

## Input

`examples/stale_ai_code.py`:

```python
from langchain.memory import ConversationBufferMemory
from sqlalchemy.ext.declarative import declarative_base


memory = ConversationBufferMemory()
Base = declarative_base()
```

## Check

```bash
llm-code-validator check examples/stale_ai_code.py
```

Expected result:

```text
examples/stale_ai_code.py:1 LCV001 warning langchain.ConversationBufferMemory ...
  fix: from langchain_community.memory import ConversationBufferMemory
examples/stale_ai_code.py:2 LCV001 warning sqlalchemy.declarative_base ...
  fix: from sqlalchemy.orm import declarative_base
```

## Preview Fix

```bash
llm-code-validator fix examples/stale_ai_code.py
```

The command previews edits without changing the file.

## Apply Safe Fixes

```bash
llm-code-validator fix examples/stale_ai_code.py --write
```

Expected output file:

```python
from langchain_community.memory import ConversationBufferMemory
from sqlalchemy.orm import declarative_base


memory = ConversationBufferMemory()
Base = declarative_base()
```

Only diagnostics marked `safe_fix` are written. Larger migrations, such as FastAPI lifespan rewrites or ambiguous vector database client changes, remain suggestions for human review.
