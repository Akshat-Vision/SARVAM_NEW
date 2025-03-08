from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import httpx
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from database import save_conversation, get_conversation_history, create_tables
from models import ConversationHistory
from fastapi.responses import JSONResponse
from uuid import uuid4
import json

# Load environment variables
load_dotenv()

# Load API Key
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
if not TOGETHER_API_KEY:
    raise ValueError("Missing TOGETHER_API_KEY environment variable!")

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis = None  # Will be initialized in startup_event()

# Define request body model
class ChatRequest(BaseModel):
    user_input: str

# Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )

# Query Together AI
async def query_together_ai(prompt: str) -> str:
    try:
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"}
        data = {"model": "meta-llama/Llama-2-7b-chat-hf", "messages": [{"role": "user", "content": prompt}]}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_json = response.json()

            logger.info(f"AI API Response: {json.dumps(response_json, indent=2)}")

            # Ensure response contains expected structure
            choices = response_json.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"]["content"]

    except httpx.HTTPStatusError as e:
        logger.error(f"API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return "I'm having trouble responding. Please try again later."

# Home endpoint
@app.get("/")
async def home():
    return {"message": "Chatbot API is running!"}

# Chat endpoint
@app.post("/chat/")
@limiter.limit("5/minute")
@cache(expire=60)
async def chat(request: Request, chat_request: ChatRequest):
    # Ensure valid session ID
    session_id = request.headers.get("session_id", str(uuid4()))
    try:
        uuid4(session_id)  # Validate session_id format
    except ValueError:
        session_id = str(uuid4())

    try:
        # Store user query
        await save_conversation(session_id, "user", chat_request.user_input)

        # Query AI Model
        chatbot_reply = await query_together_ai(chat_request.user_input)

        # Store AI response
        await save_conversation(session_id, "assistant", chatbot_reply)

        return {"response": chatbot_reply}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

# Startup event
@app.on_event("startup")
async def startup_event():
    global redis
    try:
        redis = aioredis.from_url(REDIS_URL)
        await create_tables()
        FastAPICache.init(RedisBackend(redis), prefix="chatbot-cache")
        logger.info("Application startup complete.")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise