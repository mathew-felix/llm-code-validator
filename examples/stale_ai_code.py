from langchain.memory import ConversationBufferMemory
from sqlalchemy.ext.declarative import declarative_base


memory = ConversationBufferMemory()
Base = declarative_base()
