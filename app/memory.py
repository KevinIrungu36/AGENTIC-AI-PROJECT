import os
from typing import List, Dict, Any
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

class MongoMemory:
    """MongoDB-backed memory for conversation context"""
    
    def __init__(self, db_name="agentic_ai", collection_name="conversations"):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")
            
        try:
            self.client = MongoClient(mongo_uri)
            # Ping to verify connection
            self.client.admin.command('ping')
            
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            
            # Create an index to quickly query a user's messages sorted by time
            self.collection.create_index([("user_id", 1), ("timestamp", -1)])
            print("✅ MongoDB Memory connected successfully!")
            
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            self.client = None
    
    def add_message(self, user_id: str, role: str, content: str):
        """Add a message to MongoDB"""
        print(f"DEBUG: Attempting to save message for {user_id}...") # Debug line
        
        if not self.client:
            print("ERROR: MongoDB client is None. The database didn't connect during startup.")
            return
            
        message = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        
        try:
            result = self.collection.insert_one(message.copy())
            print(f"✅ Successfully saved to MongoDB! Document ID: {result.inserted_id}")
        except Exception as e:
            print(f"❌ MongoDB Insert Error: {e}")
        
        self.collection.insert_one(message.copy())
    
    def get_recent_context(self, user_id: str, max_messages: int = 5) -> List[Dict]:
        """Get recent conversation context from MongoDB for a specific user"""
        if not self.client:
            return []
            
        # Find latest messages for the user, sort descending by time, limit results
        cursor = self.collection.find(
            {"user_id": user_id},
            {"_id": 0, "role": 1, "content": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(max_messages)
        
        # Convert cursor to list and reverse it to maintain chronological order for the LLM
        messages = list(cursor)
        messages.reverse()
        
        return messages
    
    def clear(self, user_id: str):
        """Clear all memory for a specific user"""
        if self.client:
            self.collection.delete_many({"user_id": user_id})