import os
from typing import Dict, Any, List
from groq import Groq
from dotenv import load_dotenv


try:
    from app.tools import SearchTool
    from app.memory import MongoMemory  # Updated import
except ImportError:

    from app.tools import SearchTool
    from app.memory import MongoMemory  # Updated import

load_dotenv()

class AIQuestionAnswerAgent:
    """AI Agent that answers questions with tool usage and memory"""
    
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
            
        self.groq_client = Groq(api_key=api_key)
        self.search_tool = SearchTool()
        
        # Initialize MongoDB Memory
        self.memory = MongoMemory() 
        

        
        self.system_prompt = """You are a helpful AI assistant that can answer questions and use tools.
    
        Guidelines:
        1. If the question is factual (about facts, data, numbers, definitions, etc.), use the search tool.
        2. For conversational questions, philosophical questions, or opinions, answer directly.
        3. Keep your responses concise and helpful.
        4. Use the conversation history for context when relevant.
        
        Always think step by step before responding."""

    def is_factual_question(self, question: str) -> bool:
        """Determine if a question is factual and requires search"""
        factual_keywords = [
            'what is', 'who is', 'when was', 'where is', 'how many', 
            'how much', 'capital of', 'population of', 'height of',
            'inventor of', 'year', 'largest', 'smallest', 'chemical symbol',
            'founder of', 'speed of', 'distance to'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in factual_keywords)
    
    def _create_message_list(self, context: List[Dict], user_message: str, is_factual: bool, tool_result: str = None) -> List[Dict]:
        """Create message list for GROQ API"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        for msg in context:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        if is_factual and tool_result:
            # Add search context for factual questions
            tool_prompt = f"""
            User Question: {user_message}
            
            Search Result: {tool_result}
            
            Based on the search result above, provide a helpful answer to the user's question.
            If the search result doesn't contain the answer, say so and provide a general response.
            """
            messages.append({"role": "user", "content": tool_prompt})
        else:
            # Add current user message for direct response
            messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def generate_response(self, user_message: str, user_id: str = "default") -> Dict[str, Any]:
        """Generate response with tool usage and memory"""
        # Add user message to MongoDB
        self.memory.add_message(user_id, "user", user_message)
        
        # Get conversation context specific to the user from MongoDB
        context = self.memory.get_recent_context(user_id)
        

        is_factual = self.is_factual_question(user_message)
        tool_result = None
        
        if is_factual:

            tool_result = self.search_tool(user_message)
        

        messages = self._create_message_list(context, user_message, is_factual, tool_result)
        

        try:
            # --- FIXED MODEL NAME ---
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b", # Changed to a valid Groq model
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )

            final_answer = response.choices.message.content
            
        except Exception as e:
            # --- ADDED DEBUG PRINT ---
            print(f"❌ Groq API Error: {e}") 
            
            if is_factual and tool_result:
                final_answer = f"Based on my search: {tool_result}"
            else:
                final_answer = "I apologize, but I'm having trouble processing your request right now. Please try again."
        
        # Add AI response to MongoDB
        self.memory.add_message(user_id, "assistant", final_answer)
        
        return {
            "response": final_answer,
            "used_tool": is_factual,
            "tool_result": tool_result
        }