from flask import Blueprint, request, jsonify, current_app
from app.utils.data_process import retrieve_and_summarize
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.database import db
from datetime import datetime

feedback_bp = Blueprint("feedback_bp", __name__)


@feedback_bp.route("/feedback", methods=["POST"])
def generate_feedback(): 
    """
    사용자로부터 user_id 와 select_date를 받아서 해당 날짜의 일기, 할일을 요약해서 피드백을 생성
    """
    data = request.json or {}
    user_id = data.get("user_id")
    select_date = data.get("select_date")
    feedback_text = data.get("feedback")

    current_app.logger.info(f"{user_id}님의 {select_date} 피드백 요청")

    if not user_id or not feedback_text:
        current_app.logger.warning(f"Missing user_id or feedback from request: {data}")
        return jsonify({"error": "Missing user_id or feedback"}), 400
    
    if not user_id or not select_date:
        return jsonify({"error": "유저 아이디 또는 날짜가 없습니다"}), 400
    
    try:
        summaries = retrieve_and_summarize(user_id, select_date)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    
    combined_summaries = summaries.get("diaries", []) + summaries.get("todo", [])
    feedback_prompt = f"다음 요약된 내용들을 참고하여서 오늘 하루에 대한 피드백을 제공해줘\n" + "\n".join(combined_summaries) + "\n\n 피드백:"
    feedback = llm_service.generate_feedback(feedback_prompt)


    # DB 저장
    save_ai_response(user_id, f"{select_date} Feedback", feedback)

    return jsonify({"feedback": feedback}), 200
