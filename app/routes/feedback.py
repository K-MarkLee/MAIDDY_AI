# MAIDDY_AI/app/routes/feedback.py

from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.models import AiResponse, Summary
from app.database import db
from datetime import datetime
from app.utils.jwt_utils import require_jwt
from flask_jwt_extended import get_jwt_identity
from app.models import Diary, Todo, Schedule

feedback_bp = Blueprint("feedback_bp", __name__)
llm_service = LLMService()


@feedback_bp.route("/feedback", methods=["POST"])
@require_jwt
def provide_feedback(user):
    """
    사용자의 하루 데이터를 분석하여 그날의 피드백을 제공.
    
    JSON 예시:
    {
        "date": "2025-01-10"
    }
    """

    data = request.json or {}
    date_str = data.get("select_date")
    
    if not date_str:
        return jsonify({"error": "원하는 날짜가 입력되지 않았습니다."}), 400
    
    try:
        select_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "올바르지 않은 형식입니다. YYYY-MM-DD 형식으로 입력해 주세요. "}), 400
    
    try:
        # 이미 피드백이 생성되었는지 확인

        existing_summary = Summary.query.filter_by(
            user_id=user.id,
            select_date=select_date,
            type="feedback"
        ).first()
        
        if existing_summary:
            current_app.logger.info(f"{user.user_name}님의 피드백이 이미 생성되었습니다. on {date_str}")
            # 기존 AI 응답 조회
            existing_response = AiResponse.query.filter_by(
                user_id=user.id,
                query=f"{select_date}의 하루를 평가해주세요."
            ).first()
            if existing_response:
                return jsonify({"feedback": existing_response.answer}), 200
            else:
                return jsonify({"error": "Feedback already exists but AI response not found."}), 500
        

        # 해당 날짜의 데이터 수집
        diaries = Diary.query.filter_by(user_id=user.id, select_date=select_date).all()
        todo = Todo.query.filter_by(user_id=user.id, select_date=select_date).all()
        schedules = Schedule.query.filter_by(user_id=user.id, select_date=select_date).all()
        
        # 데이터 요약
        diary_texts = [diary.content for diary in diaries]
        todo_texts = [todo.content for todo in todo]
        schedule_texts = [f"{schedule.title}: {schedule.content}" for schedule in schedules]
        
        combined_text = "\n".join(diary_texts + todo_texts + schedule_texts)
        
        # 요약 및 임베딩 저장
        summary = llm_service.summarize_and_save(
            user_id=user.id,
            text=combined_text,
            data_type="feedback",
            select_date=select_date
        )
        
        if summary:
            # 개인화된 피드백 생성 (predefined prompt)
            feedback_prompt = f"{user.user_name}님의 {select_date} 하루를 평가해주세요."
            feedback_response = llm_service.generate_personalized_response(user.id, feedback_prompt)
            
            # AI 응답을 DB에 저장 (with select_date)
            save_ai_response(user.id, feedback_prompt, feedback_response, select_date=select_date)
            
            return jsonify({"feedback": feedback_response}), 200
        else:
            return jsonify({"error": "피드백 생성에 실패했습니다."}), 500
    except Exception as e:
        current_app.logger.error(f" {user.user_name}님의 피드백 제공이 실패했습니다. on {date_str}: {e}")
        return jsonify({"error": "피드백 제공에 실패했습니다."}), 500
