# MAIDDY_AI/app/routes/chatbot.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.database import db
from app.utils.jwt_utils import require_jwt


chatbot_bp = Blueprint("chatbot_bp", __name__)
llm_service = LLMService()


@chatbot_bp.route("/chatbot", methods=["POST"])
@require_jwt
def chatbot(user):
    """
    사용자로부터 JWT 토큰과 query를 받아 AI 응답을 생성.
    FAISS를 활용하여 개인화된 응답을 생성.
    
    JSON 예시:
    {
        "query": "어제 할일 중 완료하지 못한 항목을 확인해줘."
    }
    """
    data = request.json or {}
    query = data.get("query")
    
    current_app.logger.info(f"{user.user_name}님의 요청을 받았습니다. : {query}")
    
    if not query:
        current_app.logger.warning(f"요청을 찾을 수 없습니다.: {data}")
        return jsonify({"error": "요청을 찾을 수 없습니다. "}), 400
    
    # 개인화된 응답 생성
    personalized_response = llm_service.generate_personalized_response(user.id, query)
    current_app.logger.info(f"LLM response: {personalized_response}")
    
    # AI 응답을 DB에 저장
    try:
        save_ai_response(user.id, query, personalized_response)
        current_app.logger.info(f"{user.user_name}님의 응답이 성공적으로 저장되었습니다.")
    except Exception as e:
        current_app.logger.error(f"{user.user_name}님의 응답이 실패하였습니다. : {e}")
    
    return jsonify({"answer": personalized_response}), 200
