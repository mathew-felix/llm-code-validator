# test_quick.py — run this from root folder
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
