from flask import Blueprint, request, jsonify, current_app
from app.utils.data_process import retrieve_and_summarize
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.database import db
from app.models import User, Summary


recommend_bp = Blueprint("recommend_bp", __name__)
llm_service = LLMService()

@recommend_bp.route("/recommend", methods=["POST"])
def generate_recommend():
    """
    사용자로부터 user_id 와 select_date를 받아서 해당 날짜의 일기, 할일, 일정을 요약해서 추천을 생성
    """
    data = request.json or {}
    user_id = data.get("user_id")
    query = data.get("query")

    current_app.logger.info(f"{user_id}님의 {query} 추천 요청 성공")

    if not user_id or not query:
        current_app.logger.warning(f"유저 아이디 또는 정보가 없습니다: {data}")
        return jsonify({"error": "유저 아이디 또는 정보가 없습니다"}), 400
    
    user = User.query.filter_by(id=user_id).first()
    if not user:
        current_app.logger.warning(f"유저 아이디가 없습니다: {user_id}")
        return jsonify({"error": "유저 아이디가 없습니다"}), 400
    

        # 사용자 요약 데이터 수집
    recent_summaries = Summary.query.filter(
        Summary.user_id == user_id
    ).order_by(Summary.created_at.desc()).all()
    summary_texts = [summary.summary_text for summary in recent_summaries]
    combined_summary = "\n".join(summary_texts)

    # LLM을 사용하여 추천 사항 생성
    prompt = f"""
    당신은 일정 및 할일 관리 챗봇입니다. 사용자의 요약 데이터를 기반으로 추천 사항을 제안하세요.
    사용자의 과거 요약: {combined_summary}
    사용자 입력: "{query}"
    추천 사항:
    """

    try :
        recommend = llm_service.generate_direct_response(prompt)
        current_app.logger.info(f"{user_id}유저의 추천 생성 성공: {recommend}")


        # 응답 저장
        save_ai_response(user_id, query, recommend)

        return jsonify({"recommend": recommend}), 200
    except Exception as e:
        current_app.logger.error(f"추천 생성 중 오류 발생: {e}")
        return jsonify({"error": "추천 생성 중 오류 발생"}), 500
    