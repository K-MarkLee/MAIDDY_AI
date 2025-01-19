# MAIDDY_AI/app/routes/recommend.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService

recommend_bp = Blueprint('recommend', __name__)
llm_service = LLMService()

@recommend_bp.route("/", methods=["POST"])
def recommend():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
        
        # 일정 추천 생성
        recommendations = llm_service.recommend_schedule(int(user_id))
            
        return jsonify({
            "success": True,
            "recommendations": recommendations
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Recommendation error: {str(e)}")
        return jsonify({"error": str(e)}), 500
