from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from models import Base, ConversationHistory
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL environment variable!")

# Initialize SQLAlchemy with asyncpg
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Create tables
async def create_tables():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

# Save conversation history
async def save_conversation(session_id: str, role: str, message: str):
    try:
        async with AsyncSessionLocal() as db:
            conversation = ConversationHistory(session_id=session_id, role=role, message=message)
            db.add(conversation)
            await db.commit()
        logger.info(f"Conversation saved: {session_id}, {role}, {message}")
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        raise

# Fetch conversation history
async def get_conversation_history(session_id: str):
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ConversationHistory).where(ConversationHistory.session_id == session_id)
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}")
        raise