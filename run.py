#!/usr/bin/env python3
import uvicorn
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    
    # Check if groq API key is set
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("❌ ERROR: GROQ_API_KEY not found in .env file")
        print("Please add your groq API key to the .env file like this:")
        print("GROQ_API_KEY=sk-your-actual-key-here")
        exit(1)
    
    if groq_key.startswith("your_") or "example" in groq_key:
        print("❌ ERROR: Please replace the placeholder groq API key with your actual key")
        exit(1)
    
    print("✅ groq API key found")
    print("🚀 Starting AI Question-Answer Helper API...")
    print("📚 API Documentation will be available at: http://localhost:8000/docs")
    print("⏹️  Press Ctrl+C to stop the server")
    
    # Simple uvicorn run without reload
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)