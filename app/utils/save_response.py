
from app.models import AiResponse
from app.database import db
from flask import current_app
from datetime import date

def save_ai_response(user, question: str, response: str, select_date: date = None):
    """
    AI 응답을 데이터베이스에 저장.
    
    :param user_id: 사용자의 고유 ID
    :param question: 질문 내용 (predefined prompt)
    :param answer: AI의 응답
    :param select_date: 선택된 날짜 (피드백 및 recommend에 해당)
    """
    try:
        ai_resp = AiResponse(
            user_id=user.user_id,
            question=question,
            response=response,
            select_date=select_date
        )
        db.session.add(ai_resp)
        db.session.commit()
    except Exception as e:
        # 예외 발생 시 로그에 기록
        user_name = user.user_name if user else "Unknown"
        current_app.logger.error(f"{user_name}의 응답 생성을 실패하였습니다. : {e}")
