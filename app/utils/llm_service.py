"""
llm 구현
"""


# app/utils/llm_service.py

import openai
from typing import List, Optional
from decouple import config
from app.models import Summary
from app.database import db
from flask import current_app
from datetime import datetime
from app.utils.faiss_service import FAISSService


    


# OpenAI API 키 설정
openai.api_key = config("OPENAI_API_KEY")

class LLMService:
    """
    LLM 서비스 클래스 , OpenAI API를 사용하여 LLM을 구현
    """
    def __init__(self, model_name = "gpt-4o-mini", embedding_dim=768, faiss_index_dir = 'faiss.indexs'):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.faiss_service = FAISSService(embedding_dim, faiss_index_dir)




    def summarize_and_save(self, user_id: int, text: str, data_type: str, select_date: datetime.date) -> Optional[Summary]:       
        """
        텍스트를 요약하고 Summary 모델에 저장합니다.
        
        :param user_id: 사용자 ID
        :param text: 요약할 텍스트
        :param data_type: 'todo','schedule','Duary' 중 하나
        :param select_date: 해당 데이터의 날짜
        :return: 생성된 Summary 객체 또는 None
        """
        try:
            # 텍스트 요약
            prompt = f"다음 주어진 텍스트를 요약하거나 핵심 키워드만 뽑아줘 : \n{text}\n\n요약:"
            response = openai.Completion.create(
                engine = "gpt-4o-mini",
                prompt = prompt,
                max_tokens = 200,
                temperature = 0.3
            )
            summary_text = response.choices[0].text.strip()

            # 요약 저장
            summary = Summary(
                user_id=user_id,
                summary_text=summary_text,
                type=data_type,
                select_date=select_date,
                created_at=datetime.now()
            )
            db.session.add(summary)
            db.session.commit()

            # 임배딩 생성 및 FAISS에 저장
            embedding = self.embed_text(summary_text)
            if embedding:
                self.faiss_service.add_embedding(embedding, user_id, summary.id)

            return summary
        
        except Exception as e:
            current_app.logger.error(f"텍스트를 요약하고 저장하는것에 실패했습니다.: {e}")
            return None




    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        텍스트를 Embedding으로 변환
        :param text: 텍스트
        :return : Embedding 백터 리스트 또는 None
        """
        try:
            response = openai.Embedding.create(
                input = text,
                model = "text-embedding-3-small"
            )
            embedding = response['data'][0]['embedding']
            return embedding
        except Exception as e:
            current_app.logger.error(f"텍스트를 Embedding으로 변환 중 오류 발생: {e}")
            return None




    def generate_personalized_response(self, user_id: int, query: str) -> str:
        """
        개인화된 응답을 생성 (FAISS를 활용하여 사용자 자신의 데이터를 검색 후 LLM에 전달).
        """
        try:
            # Query embedding
            query_embedding = self.embed_text(query)
            if not query_embedding:
                return "죄송합니다. 응답을 생성할 수 없습니다."
            
            # FAISS 검색: 사용자 자신의 인덱스에서 유사한 요약 검색
            distances, summary_ids = self.faiss_service.search(query_embedding, user_id, top_k=10)
            
            if not summary_ids:
                return "죄송합니다. 개인화된 정보를 제공할 수 없습니다."

            # 유사한 요약 데이터 수집
            similar_summaries = Summary.query.filter(Summary.id.in_(summary_ids)).all()
            combined_summary = "\n".join([summary.summary_text for summary in similar_summaries])

            
            prompt = f"""
            당신은 {user_id}의 일정 및 할일 관리 챗봇입니다. 다음은 {user_id}의 요약 정보입니다:
            {combined_summary}
            
            {user_id}님의 질문: "{query}"
            응답:
            """
            
            response = openai.Completion.create(
                engine="gpt-4o-mini",
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].text.strip()
        except Exception as e:
            current_app.logger.error(f"Failed to generate personalized response for user {user_id}: {e}")
            return "죄송합니다. 응답을 생성하는 데 문제가 발생했습니다."