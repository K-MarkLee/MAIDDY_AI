# MAIDDY_AI/app/routes/feedback.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)
llm_service = LLMService()

@feedback_bp.route("/", methods=["POST"])
async def get_feedback():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        select_date = data.get("date")
        
        if select_date:
            select_date = datetime.strptime(select_date, "%Y-%m-%d").date()
        else:
            select_date = datetime.now().date()
        
        feedback = await llm_service.generate_feedback(user_id, select_date)
        
        save_ai_response(
            user_id=user_id,
            question=f"{select_date} 피드백 요청",
            response=feedback,
            response_type="feedback",
            select_date=select_date
        )
            
        return jsonify(feedback), 200
        
    except Exception as e:
        current_app.logger.error(f"Feedback error: {str(e)}")
        return jsonify({"error": str(e)}), 500