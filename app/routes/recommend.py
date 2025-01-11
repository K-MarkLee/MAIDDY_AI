from flask import Blueprint, request, jsonify
from app.utils.data_process import retrieve_and_summarize
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response


recommend_bp = Blueprint("recommend_bp", __name__)
llm_service = LLMService()

@recommend_bp.route("/recommend", methods=["POST"])
def generate_recommend():
    """
    사용자로부터 user_id 와 select_date를 받아서 해당 날짜의 일기, 할일, 일정을 요약해서 추천을 생성
    """
    data = request.json or {}
    user_id = data.get("user_id")
    select_date = data.get("select_date")

    if not user_id or not select_date:
        return jsonify({"error": "유저 아이디 또는 날짜 정보가 없습니다"}), 400
    
    try:
        summaries = retrieve_and_summarize(user_id, select_date)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    

    combined_summaries = summaries.get("diaries", []) + summaries.get("todo", []) + summaries.get("schedules", [])
    recommend_prompt = f"다음 요약된 내용들을 참고하여서 개인적으로 일정을 추천해서 알려줘. 단답식 ~추천합니다 식으로.\n" + "\n".join(combined_summaries) + "\n\n 추천:"
    recommend = llm_service.generate_recommend(recommend_prompt)


    # DB 저장
    save_ai_response(user_id, f"{select_date} Recommend", recommend)

    return jsonify({"recommend": recommend}), 200
