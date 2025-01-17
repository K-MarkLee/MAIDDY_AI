from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response

chatbot_bp = Blueprint('chatbot', __name__)
llm_service = LLMService()

@chatbot_bp.route("/chatbot", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        query = data.get("query")
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        if not query:
            return jsonify({"error": "Query is required"}), 400
            
        import asyncio
        response = asyncio.run(llm_service.chatbot(int(user_id), query))
        
        save_ai_response(
            user_id=int(user_id),
            question=query,
            response=response,
            response_type="chat"
        )
            
        return jsonify({"response": response}), 200
        
    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500