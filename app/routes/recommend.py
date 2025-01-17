# MAIDDY_AI/app/routes/recommend.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response

recommend_bp = Blueprint('recommend', __name__)
llm_service = LLMService()

@recommend_bp.route("/", methods=["GET"])
async def get_recommendations():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        recommendations = await llm_service.generate_recommendations(user_id)
        
        save_ai_response(
            user_id=user_id,
            question="추천 요청",
            response=recommendations,
            response_type="recommend"
        )
            
        return jsonify(recommendations), 200
        
    except Exception as e:
        current_app.logger.error(f"Recommendation error: {str(e)}")
        return jsonify({"error": str(e)}), 500
