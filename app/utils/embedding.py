from datetime import datetime, timedelta
from typing import List, Tuple
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.schema import SystemMessage, HumanMessage
from app.models import CleanedData, Summary, Embedding
from app.extensions import db
from flask import current_app


class EmbeddingService:
    def __init__(self):
        self.llm = None
        self.embedding_model = None
        
    def _init_model(self):
        if not self.llm:
            self.llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                temperature=current_app.config['OPENAI_TEMPERATURE'],
                api_key=current_app.config['OPENAI_API_KEY']
            )
        if not self.embedding_model:
            self.embedding_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=current_app.config['OPENAI_API_KEY']
            )

    def get_week_dates(self, date: datetime.date) -> Tuple[datetime.date, datetime.date]:
        start_date = date - timedelta(days=date.weekday())  # 월요일
        end_date = start_date + timedelta(days=6)  # 일요일
        return start_date, end_date

    def process_weekly_data(self, user_id: int, date: datetime.date) -> Tuple[bool, str]:
        self._init_model()
        
        try:
            start_date, end_date = self.get_week_dates(date)
            
            cleaned_data = CleanedData.query.filter(
                CleanedData.user_id == user_id,
                CleanedData.select_date >= start_date,
                CleanedData.select_date <= end_date
            ).order_by(CleanedData.select_date).all()
            
            if not cleaned_data:
                return False, "해당 주의 데이터가 없습니다."
            
            combined_text = "\n\n".join([
                f"{data.select_date.strftime('%Y-%m-%d')}:\n{data.cleaned_text}" 
                for data in cleaned_data
            ])
            
            try:
                summary_text = self._create_weekly_summary(combined_text)
                
                summary = Summary(
                    user_id=user_id,
                    summary_text=summary_text,
                    type='weekly',
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(summary)
                
                embedding_vector = self._create_embedding(summary_text)
                embedding = Embedding(
                    user_id=user_id,
                    summary_id=summary.id,
                    type='weekly',
                    embedding=embedding_vector,
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(embedding)
                
                for data in cleaned_data:
                    db.session.delete(data)
                
                db.session.commit()
                return True, "주간 데이터 처리 완료"
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"주간 데이터 처리 중 오류가 발생했습니다.: {str(e)}")
                return False, "주간 데이터 처리 중 오류가 발생했습니다."
            
        except Exception as e:
            current_app.logger.error(f"주간 데이터 처리 중 오류가 발생했습니다.: {str(e)}")
            return False, "주간 데이터 처리 중 오류가 발생했습니다."

    def _create_weekly_summary(self, text: str) -> str:
        try:
            system_prompt = """
            일주일간의 데이터를 다음 기준으로 요약해주세요:
            1. 중요한 사건과 활동을 시간순으로 정리
            2. 주요 성과와 진행 상황
            3. 반복되는 패턴이나 특이사항
            4. 감정과 컨디션의 변화
            
            요약은 최대한 압축하되, 중요한 정보는 모두 포함해야 합니다.
            데이터의 select_date는 해당날짜를 의미합니다.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=text)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            current_app.logger.error(f"주간 데이터 요약 생성 중 오류가 발생했습니다.: {str(e)}")
            raise

    def _create_embedding(self, text: str) -> List[float]:
        try:
            if not self.embedding_model:
                self._init_model()
                
            if not self.embedding_model:
                raise ValueError("임베딩 모델 초기화 실패")
                
            embedding = self.embedding_model.embed_query(text)
            return embedding
        except Exception as e:
            current_app.logger.error(f"임베딩 생성 중 오류가 발생했습니다.: {str(e)}")
            raise