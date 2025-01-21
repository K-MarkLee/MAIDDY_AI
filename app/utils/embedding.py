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
        """LLM 모델 초기화"""
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
        """주어진 날짜가 속한 주의 시작일(월요일)과 종료일(일요일) 반환"""
        start_date = date - timedelta(days=date.weekday())  # 월요일
        end_date = start_date + timedelta(days=6)  # 일요일
        return start_date, end_date

    def process_weekly_data(self, user_id: int, date: datetime.date) -> Tuple[bool, str]:
        """주간 데이터 처리
        1. 해당 주의 CleanedData 수집
        2. 데이터 요약
        3. 임베딩 생성
        4. CleanedData 삭제
        """
        self._init_model()
        
        try:
            # 주의 시작일과 종료일 계산
            start_date, end_date = self.get_week_dates(date)
            
            # 해당 주의 CleanedData 수집
            cleaned_data = CleanedData.query.filter(
                CleanedData.user_id == user_id,
                CleanedData.select_date >= start_date,
                CleanedData.select_date <= end_date
            ).order_by(CleanedData.select_date).all()
            
            # 데이터가 하나도 없으면 처리하지 않음
            if not cleaned_data:
                return False, "해당 주의 데이터가 없습니다."
            
            # 데이터 텍스트 결합
            combined_text = "\n\n".join([
                f"{data.select_date.strftime('%Y-%m-%d')}:\n{data.cleaned_text}" 
                for data in cleaned_data
            ])
            
            try:
                # 주간 데이터 요약
                summary_text = self._create_weekly_summary(combined_text)
                
                # Summary 모델에 저장
                summary = Summary(
                    user_id=user_id,
                    summary_text=summary_text,
                    type='weekly',
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(summary)
                
                # 임베딩 생성 및 저장
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
                
                # CleanedData 삭제
                for data in cleaned_data:
                    db.session.delete(data)
                
                db.session.commit()
                return True, "주간 데이터 처리 완료"
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error in data processing: {str(e)}")
                return False, "데이터 처리 중 오류가 발생했습니다."
            
        except Exception as e:
            current_app.logger.error(f"Error in process_weekly_data: {str(e)}")
            return False, "데이터 처리 중 오류가 발생했습니다."

    def _create_weekly_summary(self, text: str) -> str:
        """주간 데이터 요약 생성"""
        try:
            system_prompt = """
            일주일간의 데이터를 다음 기준으로 요약해주세요:
            1. 중요한 사건과 활동을 시간순으로 정리
            2. 주요 성과와 진행 상황
            3. 반복되는 패턴이나 특이사항
            4. 감정과 컨디션의 변화
            
            요약은 최대한 압축하되, 중요한 정보는 모두 포함해야 합니다.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=text)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            current_app.logger.error(f"Error in _create_weekly_summary: {str(e)}")
            raise

    def _create_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        try:
            if not self.embedding_model:
                self._init_model()
                
            if not self.embedding_model:
                raise ValueError("임베딩 모델 초기화 실패")
                
            embedding = self.embedding_model.embed_query(text)
            return embedding
        except Exception as e:
            current_app.logger.error(f"Embedding creation error: {str(e)}")
            raise