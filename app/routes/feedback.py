# MAIDDY_AI/app/routes/feedback.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.models import Diary
from sqlalchemy import and_
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)
llm_service = LLMService()

@feedback_bp.route("/", methods=["POST"])
def feedback():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        select_date = data.get("select_date")
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
            
        if not select_date:
            return jsonify({"error": "select_date가 필요합니다."}), 400
            
        try:
            select_date = datetime.strptime(select_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "select_date는 'YYYY-MM-DD' 형식이어야 합니다."}), 400
            
        # 해당 날짜의 일기 존재 여부 확인
        diary = Diary.query.filter(
            and_(
                Diary.user_id == user_id,
                Diary.select_date == select_date
            )
        ).first()
        
        if not diary:
            return jsonify({
                "success": False,
                "message": f"{select_date} 날짜의 일기를 먼저 작성해주세요."
            }), 400
            
        # 피드백 생성
        feedback = llm_service.generate_daily_feedback(int(user_id), select_date)
            
        return jsonify({
            "success": True,
            "feedback": feedback
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Feedback error: {str(e)}")
        return jsonify({"error": str(e)}), 500