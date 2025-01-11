from app.models import AiResponse
from app.database import db
from app.utils.llm_service import LLMService

llm_service = LLMService()


def save_ai_response(user_id: str, question: str, response: str): # ai의 응답을 저장하는 함수
    embedding = llm_service.get_embedding(response)
    ai_response = AiResponse(user_id=user_id, question=question, response=response, embedding = embedding)
    db.session.add(ai_response)
    db.session.commit()