from app.models import AiResponse, User
from app.extensions import db
from datetime import datetime
from flask import current_app
from typing import Optional, Dict, Any
import json

def save_feedback_response(
    user_id: int, 
    feedback_data: Dict[str, Any], 
    select_date: datetime.date
) -> Optional[AiResponse]:
    """
    AI의 피드백 응답을 데이터베이스에 저장하는 함수
    
    Args:
        user_id (int): 사용자 ID
        feedback_data (Dict): AI가 생성한 피드백 데이터
        select_date (datetime.date): 피드백 대상 날짜
    """
    try:
        # 피드백 데이터를 JSON 문자열로 변환
        feedback_text = json.dumps(feedback_data, ensure_ascii=False)
        
        # 피드백 응답 저장
        ai_response = AiResponse(
            user_id=user_id,
            question=f"{select_date} 일자 피드백 요청",  # 질문 필드에 날짜 정보 포함
            response=feedback_text,
            select_date=select_date,
            response_type="feedback"  # 응답 유형을 feedback으로 고정
        )
        
        db.session.add(ai_response)
        db.session.commit()
        
        current_app.logger.info(
            f"피드백 저장 완료 - "
            f"user_id: {user_id}, "
            f"date: {select_date}"
        )
        
        return ai_response
    
    except Exception as e:
        current_app.logger.error(
            f"피드백 저장 실패 - "
            f"user_id: {user_id}, "
            f"date: {select_date}, "
            f"error: {str(e)}"
        )
        db.session.rollback()
        return None
