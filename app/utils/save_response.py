from app.models import AiResponse, User
from app.extensions import db
from datetime import datetime
from flask import current_app
from typing import Optional, Dict, Any
import json

def save_ai_response(
    user_id: int, 
    question: str, 
    response: str | Dict[str, Any], 
    select_date: Optional[datetime.date] = None,
    response_type: str = "chat"
) -> Optional[AiResponse]:
    """
    AI 응답을 데이터베이스에 저장하는 함수
    
    Args:
        user_id (int): 사용자 ID
        question (str): 사용자의 질문 또는 요청
        response (str | Dict): AI의 응답 (문자열 또는 구조화된 데이터)
        select_date (datetime.date, optional): 선택된 날짜
        response_type (str): 응답 유형 (chat, feedback, recommend)
    """
    try:
        # 날짜 설정
        if select_date is None:
            select_date = datetime.now().date()

        # 응답 데이터 처리
        if isinstance(response, dict):
            response_text = json.dumps(response, ensure_ascii=False)
        else:
            response_text = str(response)

        # 응답 저장
        ai_response = AiResponse(
            user_id=user_id,
            question=question,
            response=response_text,
            select_date=select_date,
            response_type=response_type
        )
        
        db.session.add(ai_response)
        db.session.commit()
        
        current_app.logger.info(
            f"AI 응답 저장 완료 - "
            f"user_id: {user_id}, "
            f"type: {response_type}, "
            f"date: {select_date}"
        )
        
        return ai_response
    
    except Exception as e:
        current_app.logger.error(
            f"AI 응답 저장 실패 - "
            f"user_id: {user_id}, "
            f"error: {str(e)}"
        )
        db.session.rollback()
        return None
