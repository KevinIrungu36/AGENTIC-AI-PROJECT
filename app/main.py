from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from typing import Optional
import os

# Import our agent
try:
    from app.agent import AIQuestionAnswerAgent
    agent_instance = AIQuestionAnswerAgent()
    print("✅ Agent initialized successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    agent_instance = None
except Exception as e:
    print(f"❌ Agent initialization error: {e}")
    agent_instance = None

app = FastAPI(
    title="AI Question-Answer Helper",
    description="A simple AI agent that answers user questions with search tool integration",
    version="1.0.0"
)

# --- ADD CORS MIDDLEWARE ---
# This allows your frontend to communicate with your backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (update this to your frontend URL in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    used_tool: bool
    tool_result: Optional[str] = None
    status: str

class ClearRequest(BaseModel):
    user_id: Optional[str] = "default"

@app.get("/")
async def root():
    return {
        "message": "AI Question-Answer Helper API is running!",
        "status": "healthy" if agent_instance else "agent_not_initialized"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint that processes user messages"""
    try:
        if not agent_instance:
            raise HTTPException(
                status_code=500, 
                detail="AI agent is not initialized."
            )
            
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Generate response using the agent
        result = agent_instance.generate_response(request.message.strip(), request.user_id)
        
        return ChatResponse(
            response=result["response"],
            used_tool=result["used_tool"],
            tool_result=result.get("tool_result"),
            status="success"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# --- ADD CLEAR ENDPOINT ---
@app.post("/clear")
async def clear_memory(request: ClearRequest):
    """Endpoint to clear a user's conversation history"""
    try:
        if agent_instance and hasattr(agent_instance, 'memory'):
            agent_instance.memory.clear(request.user_id)
            return {"status": "success", "message": f"Memory cleared for user: {request.user_id}"}
        else:
            raise HTTPException(status_code=500, detail="Memory module not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.get("/health")
async def health_check():
    agent_status = "healthy" if agent_instance else "unhealthy"
    return {
        "status": agent_status, 
        "service": "AI Question-Answer Helper",
        "agent_initialized": agent_instance is not None
    }