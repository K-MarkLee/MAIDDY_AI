from flask import Blueprint, request, jsonify
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.models import Schedule, AiResponse
from app.database import db
from datetime import datetime

chatbot_bp = Blueprint("chatbot_bp", __name__)
llm_service = LLMService()


@chatbot_bp.route("/chatbot", methods=["POST"])
def chatbot():
    """
    사용자로부터 user_id 와 prompt를 받아서 LLM을 통해 답변을 생성 (일정 추가와 같은 기능 가능)
    """
    
    data = request.json or {}
    user_id = data.get("user_id")
    prompt = data.get("prompt")

    if not user_id or not prompt:
        return jsonify({"error": "유저 아이디 또는 프롬프트가 없습니다"}), 400

    # LLM 응답 생성 (예: agent_service)
    response = llm_service.simple_chat(prompt)

    # DB 저장
    ai_response = AiResponse(user_id=user_id, question = prompt, responser = response)
    db.session.add(ai_response)
    db.session.commit()

    return jsonify({"response": response}), 200

