# MAIDDY_AI/app/routes/recommend.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.models import Schedule, Todo, AiResponse, User, Summary, Diary
from app.database import db
from app.utils.other_utils import TokenManager
from app.utils.jwt_utils import require_jwt

recommend_bp = Blueprint("recommend_bp", __name__)
llm_service = LLMService()
token_manager = TokenManager()

@recommend_bp.route("/recommend", methods=["GET"])
@require_jwt
def recommend(user):
    """
    개인화된 추천 제공.
    
    Response 예시:
    {
        "recommendations": [
            "오늘의 운동 계획은...",
            "추천하는 독서 목록은..."
        ]
    }
    """
    try:
        # 추천을 위한 기본 질문 생성 (predefined prompt)
        query = f"{user.user_name}님의 일정을 분석하여 추천을 부탁드립니다."
        
        # 개인화된 응답 생성
        recommendation_response = llm_service.generate_personalized_response(user.id, query)
        
        # AI 응답을 DB에 저장
        save_ai_response(user.id, query, recommendation_response)
        
        # 응답을 줄 수 있는 적절한 형식으로 변환 (예: 줄바꿈 기준 분할)
        recommendations = [rec.strip() for rec in recommendation_response.split('\n') if rec.strip()]
        
        return jsonify({"recommendations": recommendations}), 200
    except Exception as e:
        current_app.logger.error(f" {user.user_name}님의 추천 제공이 실패하였습니다. : {e}")
        return jsonify({"error": "추천 제공에 실패했습니다."}), 500
