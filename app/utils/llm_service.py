from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from app.models import Todo, Diary, Schedule, CleanedData, Feedback, Summary, Embedding
from app.extensions import db
from flask import current_app
from app.utils.embedding import EmbeddingService

class LLMService:
    def __init__(self):
        self.chat_model = None
        self.embedding_service = None
        
    def _init_model(self):
        """모델 초기화"""
        if not self.chat_model:
            self.chat_model = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                temperature=current_app.config['OPENAI_TEMPERATURE'],
                api_key=current_app.config['OPENAI_API_KEY']
            )
           
    def _init_embedding_service(self):
        """임베딩 서비스 초기화"""
        if not self.embedding_service:
            self.embedding_service = EmbeddingService()

    def _get_similar_summaries(self, user_id: int, query: str, limit: int = 3) -> List[str]:
        """유사한 주간 요약 검색"""
        self._init_embedding_service()
        self.embedding_service._init_model()  # 임베딩 모델 초기화 추가
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedding_service._create_embedding(query)
            
            # Vector 검색
            similar_summaries = Embedding.query.filter_by(
                user_id=user_id,
                type='weekly'
            ).order_by(
                Embedding.embedding.cosine_distance(query_embedding)
            ).limit(limit).all()
            
            # 관련 Summary 텍스트 가져오기
            summary_texts = []
            for emb in similar_summaries:
                summary = Summary.query.get(emb.summary_id)
                if summary:
                    summary_texts.append(f"{summary.start_date.strftime('%Y-%m-%d')}~{summary.end_date.strftime('%Y-%m-%d')}: {summary.summary_text}")
            
            return summary_texts
        except Exception as e:
            current_app.logger.error(f"Error in _get_similar_summaries: {str(e)}")
            return []

    def get_daily_data(self, user_id: int, select_date: datetime.date) -> Tuple[bool, Optional[Dict], str]:
        """사용자의 일일 데이터 조회
        
        Returns:
            Tuple[bool, Optional[Dict], str]: (성공 여부, 데이터 딕셔너리, 메시지)
        """
        try:
            # Todo 데이터 조회
            todos = Todo.query.filter_by(
                user_id=user_id,
                created_at=select_date
            ).all()
            
            # Diary 데이터 조회
            diary = Diary.query.filter_by(
                user_id=user_id,
                created_at=select_date
            ).first()
            
            # Schedule 데이터 조회
            schedules = Schedule.query.filter_by(
                user_id=user_id,
                created_at=select_date
            ).all()
            
            # 필수 데이터 체크
            if not todos and not diary and not schedules:
                return False, {}, "데이터가 없습니다."
            
            data = {
                'todos': [{'content': todo.content, 'is_completed': todo.is_completed, 'select_date': todo.select_date} for todo in todos],
                'diary': [{'content': diary.content, 'select_date': diary.select_date}],
                'schedules': [{'title': schedule.title, 'content': schedule.content, 'select_date': schedule.select_date} for schedule in schedules]
            }
                
            return True, data, "데이터 조회 성공"
        except Exception as e:
            current_app.logger.error(f"Error in get_daily_data: {str(e)}")
            return False, None, "데이터 조회 중 오류가 발생했습니다."

    def clean_daily_data(self, user_id: int, select_date: datetime.date) -> Tuple[bool, str]:
        """일일 데이터 전처리 및 저장"""
        self._init_model()
        self._init_embedding_service()
        
        try:
            # 데이터 조회
            success, daily_data, message = self.get_daily_data(user_id, select_date)
            if not success:
                return False, message
            
            # 데이터 텍스트 형식으로 변환
            text_content = []

            # 일기 데이터 추가 (select_date 포함)
            text_content.append(f"일기 ({daily_data['diary'][0]['select_date']}): {daily_data['diary'][0]['diary']}" if daily_data['diary'] else "")

            # 할 일 목록 추가
            todo_texts = [f"- {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                        for todo in daily_data['todos']]
            text_content.append("할 일 목록:\n" + "\n".join(todo_texts))

            # 일정 목록 추가 (select_date 포함)
            schedule_texts = [f"- {schedule['title']} ({schedule['select_date']}): {schedule['content']}" 
                            for schedule in daily_data['schedules']]
            text_content.append("일정 목록:\n" + "\n".join(schedule_texts))

            combined_text = "\n\n".join(text_content)       
            
            try:
                # LLM을 통한 텍스트 전처리
                cleaned_text = self._preprocess_text(combined_text)
            except Exception as e:
                current_app.logger.error(f"OpenAI API error: {str(e)}")
                return False, "텍스트 전처리 중 오류가 발생했습니다."
            
            try:
                # CleanedData에 저장
                cleaned_data = CleanedData(
                    user_id=user_id,
                    select_date=select_date,
                    cleaned_text=cleaned_text
                )
                db.session.add(cleaned_data)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
                return False, "데이터 저장 중 오류가 발생했습니다."
            
            return True, cleaned_text
            
        except Exception as e:
            current_app.logger.error(f"Unexpected error in clean_daily_data: {str(e)}")
            return False, "데이터 처리 중 오류가 발생했습니다."

    def get_chat_response(self, user_id: int, question: str) -> Tuple[bool, str]:
        """챗봇 응답 생성"""
        self._init_model()
        
        # 컨텍스트 수집
        contexts = []
        todaydata = []
        
        # 1. Vector 검색으로 유사한 주간 요약 찾기
        similar_summaries = self._get_similar_summaries(user_id, question)
        if similar_summaries:
            contexts.append("관련된 과거 주간 요약:")
            contexts.extend(similar_summaries)
        

        # 2. 일일 데이터 조회
        today = datetime.now().date()
        success, daily_data, message = self.get_daily_data(user_id, today)
        if success:
            # 일일 데이터를 컨텍스트에 추가
            if daily_data.get('diary'):
                diary_texts = [f"{diary['select_date']}: {diary['content']}" for diary in daily_data['diary']]
                todaydata.append(f"\n오늘의 데이터:\n" + "\n".join(diary_texts))

            if daily_data.get('todos'):
                todo_texts = [f" {todo['select_date']} : {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                            for todo in daily_data['todos']]
                todaydata.append("오늘의 할 일 목록:\n" + "\n".join(todo_texts))

            if daily_data.get('schedules'):
                schedule_texts = [f"{schedule['select_date']} : {schedule['title']} {schedule['content']}" 
                                for schedule in daily_data['schedules']]
                todaydata.append("오늘의 일정 목록:\n" + "\n".join(schedule_texts))

        else:
            contexts.append(f"일일 데이터가 없습니다. 최소 하루의 데이터를 추가하여야 결과를 얻을 수 있습니다.")


        
        # 3. 모든 일일 데이터 가져오기
        all_data = CleanedData.query.filter_by(
            user_id=user_id
        ).order_by(CleanedData.select_date.desc()).all()
        
        if all_data:
            contexts.append("\n과거 데이터:")
            for data in all_data:
                if data.select_date != today:  # 오늘 데이터는임시 제외
                    contexts.append(f"{data.select_date.strftime('%Y-%m-%d')}의 데이터:\n{data.cleaned_text}")



        system_prompt= f"""
        당신은 사용자의 일상을 관리해주는 AI 비서입니다. 현재는 유저 테스트 단계입니다.
        사용자의 일기,할 일, 일정 데이터를 기반으로 자연스럽게 대화하며 도움을 제공해주세요.

        유저 테스트를 위해서 데이터들을 자연스럽게 활용하고, 추가적으로 정보를 생각해 내어 대답해 주세요.
        항상 친절하고 공감적인 태도를 유지하면서, 실질적인 도움이 되는 답변을 제공해주세요.
        
        오늘의 데이터 {todaydata}를 메인으로 사용하고 대답을 제공해주세요.
        """

        # 메시지 구성: 시스템 프롬프트, 컨텍스트, 사용자 질문
        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content="\n".join(contexts)),
            HumanMessage(content=question)
        ]

        try:
            response = self.chat_model.invoke(messages)
            return True, response.content
        except Exception as e:
            current_app.logger.error(f"chat_model.invoke 중 오류 발생: {str(e)}")
            return False, "챗봇 응답 생성 중 오류가 발생했습니다."

    def create_feedback(self, user_id: int, select_date: datetime.date) -> Tuple[bool, str]:
        """일일 피드백 생성"""
        self._init_model()
        
        # 컨텍스트 수집
        contexts = []
        todaydata = []
        
        # 1. 모든 주간 요약 가져오기
        summaries = Summary.query.filter_by(
            user_id=user_id,
            type='weekly'
        ).order_by(Summary.end_date.desc()).limit(3).all()
        
        if summaries:
            contexts.append("주간 요약:")
            for summary in summaries:
                contexts.append(f"{summary.start_date.strftime('%Y-%m-%d')}~{summary.end_date.strftime('%Y-%m-%d')}: {summary.summary_text}")
        
        # 2. 일일 데이터 조회
        today = datetime.now().date()
        success, daily_data, message = self.get_daily_data(user_id, today)
        if success:
            # 일일 데이터를 컨텍스트에 추가
            if daily_data.get('diary'):
                diary_texts = [f"{diary['select_date']}: {diary['content']}" for diary in daily_data['diary']]
                todaydata.append(f"\n오늘의 데이터:\n" + "\n".join(diary_texts))

            if daily_data.get('todos'):
                todo_texts = [f" {todo['select_date']} : {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                            for todo in daily_data['todos']]
                todaydata.append("오늘의 할 일 목록:\n" + "\n".join(todo_texts))

            if daily_data.get('schedules'):
                schedule_texts = [f"{schedule['select_date']} : {schedule['title']} {schedule['content']}" 
                                for schedule in daily_data['schedules']]
                todaydata.append("오늘의 일정 목록:\n" + "\n".join(schedule_texts))

        else:
            contexts.append(f"일일 데이터가 없습니다. 최소 하루의 데이터를 추가하여야 결과를 얻을 수 있습니다.")


        
        # 3. 모든 일일 데이터 가져오기
        all_data = CleanedData.query.filter_by(
            user_id=user_id
        ).order_by(CleanedData.select_date.desc()).all()
        
        if all_data:
            contexts.append("\n과거 데이터:")
            for data in all_data:
                if data.select_date != today:  # 오늘 데이터는임시 제외
                    contexts.append(f"{data.select_date.strftime('%Y-%m-%d')}의 데이터:\n{data.cleaned_text}")
        

        # 유저 테스트용
        system_prompt = f"""
            사용자의 하루 데이터를 분석하여 다음과 같은 피드백을 제공해주세요:
            1. 할 일 완료율과 성취도 분석
            2. 긍정적인 부분 강조
            3. 개선이 필요한 부분에 대한 건설적인 제안
            4. 전반적인 하루 평가와 격려의 메시지

            피드백은 항상 긍정적이고 동기부여가 되는 톤을 유지하면서, 구체적이고 실천 가능한 제안을 포함해야 합니다.

            현재는 유저테스트 단계입니다.

            피드백은 오늘하루가 어땟는지 오늘의 데이터의 평가만을 해야합니다. 
            데이터를 반환하지말고, 오늘의 데이터에 대한 평가만을 적어줘.
            

            오늘의 데이터야. {todaydata}
            간단하게 1~2줄로 답변해주세요.
            """
        
        # 메시지 구성: 시스템 프롬프트와 컨텍스트
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(contexts))
        ]

        try:
            response = self.chat_model.invoke(messages)
            feedback_text = response.content

            # Feedback 모델에 저장
            feedback = Feedback(
                user_id=user_id,
                feedback=feedback_text,
                select_date=select_date
            )
            db.session.add(feedback)
            db.session.commit()

            return True, feedback_text
        except Exception as e:
            current_app.logger.error(f"Error in create_feedback: {str(e)}")
            return False, "피드백 생성 중 오류가 발생했습니다."

    def create_recommendation(self, user_id: int) -> Tuple[bool, str]:
        """일정 추천 생성"""
        self._init_model()
        
        # 컨텍스트 수집
        contexts = []
        todaydata = []
        
        # 1. 모든 주간 요약 가져오기
        summaries = Summary.query.filter_by(
            user_id=user_id,
            type='weekly'
        ).order_by(Summary.end_date.desc()).limit(3).all()
        
        if summaries:
            contexts.append("주간 요약:")
            for summary in summaries:
                contexts.append(f"{summary.start_date.strftime('%Y-%m-%d')}~{summary.end_date.strftime('%Y-%m-%d')}: {summary.summary_text}")
        

        # 2. 일일 데이터 조회
        today = datetime.now().date()
        success, daily_data, message = self.get_daily_data(user_id, today)
        if success:
            # 일일 데이터를 컨텍스트에 추가
            if daily_data.get('diary'):
                diary_texts = [f"{diary['select_date']}: {diary['content']}" for diary in daily_data['diary']]
                todaydata.append(f"\n오늘의 데이터:\n" + "\n".join(diary_texts))

            if daily_data.get('todos'):
                todo_texts = [f" {todo['select_date']} : {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                            for todo in daily_data['todos']]
                todaydata.append("오늘의 할 일 목록:\n" + "\n".join(todo_texts))

            if daily_data.get('schedules'):
                schedule_texts = [f"{schedule['select_date']} : {schedule['title']} {schedule['content']}" 
                                for schedule in daily_data['schedules']]
                todaydata.append("오늘의 일정 목록:\n" + "\n".join(schedule_texts))

        else:
            contexts.append(f"일일 데이터가 없습니다. 최소 하루의 데이터를 추가하여야 결과를 얻을 수 있습니다.")

        
        # 3. 모든 일일 데이터 가져오기
        all_data = CleanedData.query.filter_by(
            user_id=user_id
        ).order_by(CleanedData.select_date.desc()).all()
        
        if all_data:
            contexts.append("\n과거 데이터:")
            for data in all_data:
                if data.select_date != today:  # 오늘 데이터는임시 제외
                    contexts.append(f"{data.select_date.strftime('%Y-%m-%d')}의 데이터:\n{data.cleaned_text}")
        

        # 유저 테스트용
        system_prompt = f"""
            사용자의 하루 데이터를 분석하여 다음과 같은 추천을 제공해주세요:
            1. 현재 일정과 할 일을 고려한 시간 관리 제안
            2. 업무/학습 효율을 높일 수 있는 활동 추천
            3. 스트레스 해소와 휴식을 위한 활동 제안
            4. 사용자의 관심사와 목표를 고려한 새로운 활동 추천

            현재는 유저테스트 단계입니다.

            깔끔하게 정리답변해줘야해.
            오늘 일정같은거 보여주지말고 딱 추천만.
            
            오늘의 데이터야. {todaydata}
            간단하게 1~2줄로 답변해줘.

        """
        
        # 메시지 구성: 시스템 프롬프트와 컨텍스트
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(contexts))
        ]
        
        response = self.chat_model.invoke(messages)
        return True, response.content

    def _preprocess_text(self, text: str) -> str:
        """LLM을 사용한 텍스트 전처리"""
        system_prompt = """
        입력된 텍스트를 자연스럽게 정리해주세요. 
        중요한 내용은 유지하면서, 불필요한 부분은 제거하고 문장을 매끄럽게 다듬어주세요.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=text)
        ]
        
        response = self.chat_model.invoke(messages)
        return response.content