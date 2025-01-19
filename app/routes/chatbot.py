from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from datetime import datetime

chatbot_bp = Blueprint('chatbot', __name__)
llm_service = LLMService()

@chatbot_bp.route("/", methods=["POST"])
def chatbot():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        question = data.get("question")
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
            
        if not question:
            return jsonify({"error": "질문이 필요합니다."}), 400
            
        # 챗봇 응답 생성
        response = llm_service.get_chat_response(int(user_id), question)
            
        return jsonify({
            "success": True,
            "response": response
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500