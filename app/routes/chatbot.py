from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response

chatbot_bp = Blueprint('chatbot', __name__)
llm_service = LLMService()

@chatbot_bp.route("/", methods=["POST"])
async def chatbot():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        query = data.get("query")
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
            
        if not query:
            return jsonify({"error": "질문이 필요합니다."}), 400
            
        response = await llm_service.chatbot(int(user_id), query)
        
        save_ai_response(
            user_id=int(user_id),
            question=query,
            response=response,
            response_type="chatbot"
        )
            
        return jsonify({"response": response}), 200
        
    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500