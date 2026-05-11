import openai
import pinecone
import chromadb
from fastapi import FastAPI
from langchain.chat_models import ChatOpenAI
from llama_index import GPTSimpleVectorIndex
from pydantic import BaseModel, validator


app = FastAPI()


class SearchRequest(BaseModel):
    query: str

    @validator("query")
    def query_required(cls, value):
        return value


@app.on_event("startup")
async def startup():
    pinecone.init(api_key="demo", environment="us-east1-gcp")


def build_index():
    llm = ChatOpenAI()
    local_client = chromadb.Client()
    index = GPTSimpleVectorIndex([])
    return llm, local_client, index


def answer_question(request: SearchRequest):
    return openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": request.query}],
    )
