import os

from random import choices
import traceback
from datetime import datetime
from typing import Optional

import uvicorn
import groq
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

app = FastAPI(
    title="AI Question-Answer Helper",
    description="Simple AI agent with search tool - Powered by Groq-Developed by KEVIN",
    version="8.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all connections
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced knowledge base with better organization
knowledge_base = {
    # Capitals - organized by country
    "france": {"capital": "Paris", "full_answer": "The capital of France is Paris."},
    "germany": {"capital": "Berlin", "full_answer": "The capital of Germany is Berlin."},
    "italy": {"capital": "Rome", "full_answer": "The capital of Italy is Rome."},
    "spain": {"capital": "Madrid", "full_answer": "The capital of Spain is Madrid."},
    "japan": {"capital": "Tokyo", "full_answer": "The capital of Japan is Tokyo."},
    "china": {"capital": "Beijing", "full_answer": "The capital of China is Beijing."},
    "india": {"capital": "New Delhi", "full_answer": "The capital of India is New Delhi."},
    "russia": {"capital": "Moscow", "full_answer": "The capital of Russia is Moscow."},
    "brazil": {"capital": "Brasília", "full_answer": "The capital of Brazil is Brasília."},
    "canada": {"capital": "Ottawa", "full_answer": "The capital of Canada is Canada."},
    "australia": {"capital": "Canberra", "full_answer": "The capital of Australia is Canberra."},
    "kenya": {"capital": "Nairobi", "full_answer": "The capital of Kenya is Nairobi."},
    "egypt": {"capital": "Cairo", "full_answer": "The capital of Egypt is Cairo."},
    "south africa": {"capital": "Pretoria", "full_answer": "The capital of South Africa is Pretoria."},
    "nigeria": {"capital": "Abuja", "full_answer": "The capital of Nigeria is Abuja."},
    "ethiopia": {"capital": "Addis Ababa", "full_answer": "The capital of Ethiopia is Addis Ababa."},
    "ghana": {"capital": "Accra", "full_answer": "The capital of Ghana is Accra."},
    "united states": {"capital": "Washington D.C.", "full_answer": "The capital of United States is Washington D.C."},
    "united kingdom": {"capital": "London", "full_answer": "The capital of United Kingdom is London."},
    
    # Science facts
    "mount everest": {"height": "8,848 meters", "full_answer": "Mount Everest is 8,848 meters (29,029 feet) tall."},
    "telephone": {"inventor": "Alexander Graham Bell", "full_answer": "Alexander Graham Bell is credited with inventing the telephone."},
    "pacific ocean": {"size": "largest", "full_answer": "The Pacific Ocean is the largest ocean on Earth."},
    "light": {"speed": "299,792,458 m/s", "full_answer": "The speed of light in vacuum is 299,792,458 meters per second."},
    "gold": {"symbol": "Au", "full_answer": "The chemical symbol for gold is Au."},
    "oxygen": {"symbol": "O", "full_answer": "The chemical symbol for oxygen is O."},
    "water": {"formula": "H₂O", "full_answer": "The chemical formula for water is H₂O."},
    "world war ii": {"end_year": "1945", "full_answer": "World War II ended in 1945."},
    "microsoft": {"founder": "Bill Gates and Paul Allen", "full_answer": "Microsoft was founded by Bill Gates and Paul Allen."},
    "apple": {"founder": "Steve Jobs, Steve Wozniak, and Ronald Wayne", "full_answer": "Apple was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne."},
    "solar system": {"planets": "8", "full_answer": "There are 8 planets in our solar system: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune."},
    
    # General knowledge
    "python": {"description": "programming language", "full_answer": "Python is a high-level programming language known for its simplicity and readability."},
    "artificial intelligence": {"description": "AI simulation", "full_answer": "Artificial Intelligence (AI) is the simulation of human intelligence in machines."},
    "machine learning": {"description": "AI subset", "full_answer": "Machine learning is a subset of AI that enables computers to learn without being explicitly programmed."},
    "groq": {"description": "AI chip company", "full_answer": "Groq is a company that develops AI inference chips and provides fast AI API services."},
}

# --- NEW: MongoDB Memory System ---
class MongoMemory:
    """MongoDB-backed memory for conversation context"""
    def __init__(self, db_name="agentic_ai", collection_name="conversations"):
        mongo_uri = os.getenv("MONGO_URI")
        try:
            self.client = MongoClient(mongo_uri)
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            self.collection.create_index([("user_id", 1), ("timestamp", -1)])
            print("✅ MongoDB Memory connected successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            self.client = None
    
    def add_message(self, user_id: str, role: str, content: str):
        if not self.client: return
        self.collection.insert_one({
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        })
    
    def get_context(self, user_id: str, max_messages: int = 4):
        if not self.client: return []
        cursor = self.collection.find(
            {"user_id": user_id},
            {"_id": 0, "role": 1, "content": 1}
        ).sort("timestamp", -1).limit(max_messages)
        messages = list(cursor)
        messages.reverse()
        return messages
    
    def clear(self, user_id: str):
        if self.client:
            self.collection.delete_many({"user_id": user_id})

# Initialize components
memory = MongoMemory()

# Initialize Groq client
try:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    groq_client = groq.Groq(api_key=groq_api_key)
    print("✅ Groq client initialized successfully!")
except Exception as e:
    print(f"❌ Groq initialization error: {e}")
    groq_client = None

# --- REQUEST MODELS ---
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

# --- TOOLS ---
def search_tool(query: str) -> str:
    """Search the knowledge base for factual information"""
    query_lower = query.lower().strip()
    
    countries = ["france", "germany", "italy", "spain", "japan", "china", "india", "russia", 
                 "brazil", "canada", "australia", "kenya", "egypt", "south africa", "nigeria",
                 "ethiopia", "ghana", "united states", "united kingdom"]
    topics = ["capital", "population", "height", "inventor", "founder", "speed", "symbol", "formula"]
    
    found_country = next((c for c in countries if c in query_lower), None)
    
    if found_country and ("capital" in query_lower or "capital of" in query_lower):
        if found_country in knowledge_base and "capital" in knowledge_base[found_country]:
            return knowledge_base[found_country]["full_answer"]
    elif found_country and "population" in query_lower:
        if found_country in knowledge_base and "population" in knowledge_base[found_country]:
            return knowledge_base[found_country]["full_answer"]
    
    for key, value in knowledge_base.items():
        if key in query_lower and "full_answer" in value:
            return value["full_answer"]
            
    return f"I couldn't find specific information about '{query}' in my knowledge base."

def is_factual_question(question: str) -> bool:
    """Determine if a question is factual and requires search"""
    factual_keywords = [
        'what is', 'who is', 'when was', 'where is', 'how many', 
        'how much', 'capital of', 'population of', 'height of',
        'inventor of', 'year', 'largest', 'smallest', 'chemical symbol',
        'founder of', 'speed of', 'distance to', 'how tall', 'how big',
        'what are', 'who invented', 'when did', 'where are'
    ]
    return any(keyword in question.lower() for keyword in factual_keywords)

def generate_groq_response(messages: list) -> str:
    """Generate response using Groq API with heavy debugging"""
    if not groq_client:
        return "I'm currently unavailable. Please check if the Groq API key is properly configured."
    
    # Use only confirmed, active Groq models
    available_models = [
        "openai/gpt-oss-120b"
    ]
    
    for model in available_models:
        try:
            print(f"--- DEBUG: Attempting model {model} ---")
            response = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # This is where the 'list' error usually happens. 
            # We will use a more robust way to grab the content.
            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                print(f"✅ Success with {model}!")
                return content
            else:
                print(f"⚠️ API returned success but no choices: {response}")
                
        except Exception as api_error:
            # THIS PRINT IS CRITICAL - Watch your terminal for this output!
            print(f"❌ Model {model} failed with error: {str(api_error)}")
            continue
            
    return "I'm currently experiencing technical difficulties with the AI service. However, I can still answer questions using my built-in knowledge base for factual information."
# --- API ENDPOINTS ---
@app.get("/")
async def root():

    return {
        "message": "AI Question-Answer Helper API is running!",
        "status": "healthy",
        "groq_api": "connected" if groq_client else "disconnected",
        "version": "8.1.0"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
            
        # --- Update: Saving user message to MongoDB ---
        memory.add_message(request.user_id, "user", user_message)
        
        is_factual = is_factual_question(user_message)
        tool_result = None

        messages = []

        
        if is_factual:

            tool_result = search_tool(user_message)
            system_prompt = "You are a helpful AI assistant. Answer the user's question concisely using ONLY the provided Search Result."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {user_message}\n\nSearch Result: {tool_result}"}
            ]
        else:
            # --- Update: Getting user context from MongoDB ---
            context = memory.get_context(request.user_id)
            messages = [{"role": "system", "content": "You are a helpful, friendly, and concise AI assistant."}]
            for msg in context:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        ai_response = generate_groq_response(messages)
        
        # --- Update: Saving bot message to MongoDB ---
        memory.add_message(request.user_id, "assistant", ai_response)
        
        return ChatResponse(
            response=ai_response,
            used_tool=is_factual,
            tool_result=tool_result,
            status="success"
        )
        
    except Exception as e:
        print(f"❌ Server error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Update: Accept ClearRequest to prevent 422 Error ---
@app.post("/clear")
async def clear_memory(request: ClearRequest):
    """Clear conversation memory from MongoDB"""
    memory.clear(request.user_id)
    return {"status": "success", "message": f"Memory cleared for {request.user_id}"}

@app.get("/knowledge")
async def list_knowledge():
    return {"total_topics": len(knowledge_base)}

if __name__ == "__main__":
    print("🚀 Starting AI Question-Answer Helper with Groq...")
    print("📚 Open http://localhost:8000/docs for API documentation")
    # --- Update: Fixed double uvicorn execution ---
    uvicorn.run("groq_server:app", host="0.0.0.0", port=8000, reload=True)