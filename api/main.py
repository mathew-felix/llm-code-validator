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
