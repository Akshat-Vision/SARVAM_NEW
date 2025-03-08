from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
