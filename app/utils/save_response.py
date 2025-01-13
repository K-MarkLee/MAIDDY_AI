from app.models import AiResponse, Summary
from app.database import db
from app.utils.llm_service import LLMService
from flask import current_app

llm_service = LLMService()


def save_ai_response(user_id: str, question: str, response: str): # ai의 응답을 저장하는 함수
    # AiResponse 테이블에 저장
    try:
        embedding = llm_service.get_embedding(response)
        ai_response = AiResponse(user_id=user_id, question=question, response=response, embedding = embedding)
        db.session.add(ai_response)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"DB 저장 중 오류 발생: {e}")


def save_summary(user_id: str, summary_text: str): # 요약을 저장하는 함수
    # Summary 테이블에 저장
    try:
        embedding = llm_service.get_embedding(summary_text)
        summary = Summary(user_id=user_id, summary_text=summary_text, embedding=embedding)
        db.session.add(summary)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"DB 저장 중 오류 발생: {e}")