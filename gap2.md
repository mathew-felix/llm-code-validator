# Final Missing Items — Push Checklist
### llm-code-validator | Status: README done, demo wrong, 3 tasks left

***

## What Is Done

- ✅ 20 libraries, 75+ database entries
- ✅ 50 external test cases
- ✅ 71.6% precision / 76.8% recall (real numbers)
- ✅ Alias resolution fixed
- ✅ LLM over-flagging fixed
- ✅ README written — all 9 sections present and correct
- ✅ Running Locally, Tech Stack, Known Limitations, Why LangGraph — all solid

***

## What Is Still Missing (3 Things Only)

***

## TASK 1 — Record a Real Demo GIF
### Priority: 🔴 Critical | Time: 30 minutes

**What is wrong right now:**
You submitted a static `.jpg` screenshot showing the idle UI state.
The right panel says "Paste code and click Validate to see the report."
This proves the interface exists. It does not prove the tool works.
A hiring manager sees a dark text editor and learns nothing.

**Why this matters:**
The GIF is the first thing every person sees when they open your repo.
It is the 15-second proof that the tool actually does what the README claims.
Without it, the project is a README and some code — not a working tool.

**Also fix: wrong file path in README**
Your README references `assets/demo.webp`
The file must be `assets/demo.gif`
Update the README line to:
```markdown
![Demo](assets/demo.gif)
```

***

### Exactly What the GIF Must Show (15 seconds total)

**Second 0–2:** Empty textarea visible, right panel empty

**Second 2–5:** This code appears in the textarea (paste it):
```python
import pinecone
from langchain.chat_models import ChatOpenAI
import pandas as pd

pinecone.init(api_key="sk-test", environment="us-east1-gcp")
index = pinecone.Index("my-index")
llm = ChatOpenAI(model_name="gpt-4")
df = pd.DataFrame({"a": [1, 2, 3]})
df2 = df.append({"a": 4}, ignore_index=True)
```

**Second 5–6:** Click "Validate Code →" button (make this visible)

**Second 6–9:** Right panel loads — colored issue cards appear showing:
- Line numbers
- Issue type (deprecated / wrong_import / hallucinated)
- Fix suggestion text

**Second 9–15:** Hold still on the results so they are readable. End.

That is the entire demo. Nothing else needed.

***

### How to Record the GIF

**Windows (recommended — ScreenToGif):**
1. Download ScreenToGif from screentogif.com (free)
2. Open your frontend in a browser
3. Open ScreenToGif → Recorder
4. Draw the capture box over just the browser window
5. Click Record, do the demo steps above, click Stop
6. File → Save As → GIF
7. Save as `assets/demo.gif` in your project folder

**Mac (recommended — Gifski):**
1. Record screen with QuickTime → File → New Screen Recording
2. Do the demo steps, stop recording, save as .mov
3. Download Gifski from gifski.app (free on Mac App Store)
4. Drag the .mov into Gifski, export as GIF
5. Save as `assets/demo.gif`

**Any OS (browser-based):**
1. Record with Loom (loom.com — free, no install)
2. Download the .mp4 from Loom
3. Go to ezgif.com/video-to-gif
4. Upload the .mp4, set start/end time to 15 seconds
5. Download the GIF
6. Save as `assets/demo.gif`

**After saving:**
```bash
# Confirm the file is in the right place
ls assets/
# Should show: demo.gif

# Update the README path if you haven't already
# Change: ![Demo](assets/demo.webp)
# To:     ![Demo](assets/demo.gif)
```

***

## TASK 2 — Three Safety Checks Before Push
### Priority: 🟡 Important | Time: 45 minutes total

These three checks take 15 minutes each.
Skipping any one of them is a common reason projects break
when someone else tries to clone them.

***

### Check A — Pin All Dependencies (15 minutes)

**What to do:**
```bash
pip freeze > requirements.txt
```

**Then open requirements.txt and confirm these are present with == not >=:**
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

If your installed versions differ slightly from the above, keep your
actual installed versions — just make sure they use `==` pinning.

**Why this matters:**
Without pinned versions, `pip install -r requirements.txt` installs
whatever the latest version is on the day someone clones it.
LangGraph and LangChain break between minor versions constantly.
A fresh clone 3 months from now will fail silently if versions float.

***

### Check B — Verify .env Is Excluded From Git (10 minutes)

**What to do:**
```bash
git status
```

Confirm `.env` does NOT appear in the output under any category
(untracked, modified, staged).

If `.env` appears anywhere:
```bash
echo ".env" >> .gitignore
git rm --cached .env
git add .gitignore
```

**Also confirm .gitignore contains all of these:**
```
.env
venv/
__pycache__/
*.pyc
.DS_Store
*.egg-info/
```

**Why this matters:**
One accidental API key commit is a real security incident.
GitHub scans for exposed keys and notifies OpenAI automatically.
OpenAI will rotate your key. You will lose access mid-demo.
Check this manually. Do not assume .gitignore is correct.

***

### Check C — Fresh Clone Test (20 minutes)

**What this is:**
Clone your own repo into a completely new empty folder and follow
your own README to get it running from scratch. Pretend you are
a hiring manager who just found your project and wants to try it.

**What to do:**
```bash
# Clone into a temp folder — NOT your existing project folder
cd /tmp
git clone https://github.com/[your-username]/llm-code-validator fresh-test
cd fresh-test

# Follow your own README exactly
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Open .env and add your real OPENAI_API_KEY
uvicorn api.main:app --reload
```

Open `frontend/index.html` in your browser.
Paste the demo code. Click Validate. Confirm results appear.

**What to look for if it breaks:**
- Missing package in requirements.txt → add it, re-pin
- .env.example missing a variable the code needs → add the variable
- File path error on startup → check os.path.join usage
- Port conflict → kill other processes on port 8000

**Why this matters:**
Your current project folder has your venv, your .env, and 3 days
of context baked in. A fresh clone has none of that.
This test finds every assumption you made that you forgot to document.
It is the single most valuable 20 minutes you can spend before pushing.

***

## TASK 3 — Push and Verify on GitHub
### Priority: 🟡 | Time: 15 minutes

After Tasks 1 and 2 are complete:

```bash
cd /path/to/your/project   # your original folder, not /tmp
git add .
git commit -m "feat: add demo GIF, pin requirements, complete README"
git push origin main
```

**Then open your GitHub repo in a browser and check 5 things:**

1. ✅ README renders with the GIF playing at the top
2. ✅ Mermaid diagram renders correctly (if it shows raw code, switch to PNG)
3. ✅ No `.env` file visible in the file list
4. ✅ `assets/demo.gif` exists and plays when clicked
5. ✅ `requirements.txt` is present with pinned versions

If the Mermaid diagram shows raw code instead of a visual:
Go to excalidraw.com, redraw the flow diagram, export as PNG,
save as `assets/architecture.png`, add this to README:
```markdown
![Architecture](assets/architecture.png)
```
Remove the Mermaid code block.

***

## Complete Day Schedule

| Time Block | Task | Done When |
|------------|------|-----------|
| First 30 min | Record demo GIF using the exact code above | `assets/demo.gif` file exists |
| Next 5 min | Update README path from demo.webp → demo.gif | README saved |
| Next 15 min | Run pip freeze, verify pinned versions | requirements.txt updated |
| Next 10 min | Run git status, verify .env excluded | No .env in git status |
| Next 20 min | Fresh clone test in /tmp | Runs clean on first try |
| Final 15 min | Push + verify 5 things on GitHub | Repo live, GIF plays |

**Total time remaining: Under 2 hours.**

***

## What the Project Looks Like After This

| Evidence | Signal to Hiring Manager |
|----------|--------------------------|
| GIF showing results appearing | "It works — I saw it in 15 seconds" |
| 71.6% precision on 50 external cases | "They measured against real data" |
| Honest Known Limitations section | "They know the boundaries of their own tool" |
| "Why LangGraph" paragraph | "They understand the architecture" |
| Fresh clone passes | "Any engineer can run this" |
| Pinned requirements.txt | "They care about reproducibility" |

This is a finished, honest, technically credible project.
Two hours of work. Then push and move on.