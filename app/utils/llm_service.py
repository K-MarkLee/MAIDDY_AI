from datetime import datetime, timedelta
from typing import Dict, Tuple
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from app.models import Todo, Diary, Schedule, CleanedData, Feedback
from app.extensions import db
from flask import current_app

class LLMService:
    def __init__(self):
        self.llm = None
        
    def _init_model(self):
        """LLM 모델 초기화"""
        if not self.llm:
            self.llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                temperature=current_app.config['OPENAI_TEMPERATURE'],
                api_key=current_app.config['OPENAI_API_KEY']
            )

    def get_daily_data(self, user_id: int, select_date: datetime.date) -> Tuple[bool, Dict, str]:
        """사용자의 일일 데이터 조회
        
        Returns:
            Tuple[bool, Dict, str]: (성공 여부, 데이터 딕셔너리, 메시지)
        """
        # Todo 데이터 조회
        todos = Todo.query.filter_by(
            user_id=user_id,
            select_date=select_date
        ).all()
        
        # Diary 데이터 조회
        diary = Diary.query.filter_by(
            user_id=user_id,
            select_date=select_date
        ).first()
        
        # Schedule 데이터 조회
        schedules = Schedule.query.filter_by(
            user_id=user_id,
            select_date=select_date
        ).all()
        
        # 필수 데이터 체크
        if not todos:
            return False, {}, f"{select_date.strftime('%Y-%m-%d')}의 할 일 데이터가 없습니다."
        
        if not diary:
            return False, {}, f"{select_date.strftime('%Y-%m-%d')}의 일기 데이터가 없습니다."
        
        if not schedules:
            return False, {}, f"{select_date.strftime('%Y-%m-%d')}의 일정 데이터가 없습니다."
        
        data = {
            'todos': [{'content': todo.content, 'is_completed': todo.is_completed} for todo in todos],
            'diary': diary.content,
            'schedules': [{'title': schedule.title, 'content': schedule.content} for schedule in schedules]
        }
        
        return True, data, "데이터 조회 성공"

    def clean_daily_data(self, user_id: int, select_date: datetime.date) -> Tuple[bool, str]:
        """일일 데이터 전처리 및 저장"""
        self._init_model()
        
        try:
            # 데이터 조회
            success, daily_data, message = self.get_daily_data(user_id, select_date)
            if not success:
                return False, message
            
            # 데이터 텍스트 형식으로 변환
            text_content = []
            
            text_content.append(f"일기: {daily_data['diary']}")
            
            todo_texts = [f"- {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                         for todo in daily_data['todos']]
            text_content.append("할 일 목록:\n" + "\n".join(todo_texts))
            
            schedule_texts = [f"- {schedule['title']}: {schedule['content']}" 
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
        
        # 오늘 날짜의 CleanedData 조회
        today = datetime.now().date()
        cleaned_data = CleanedData.query.filter_by(
            user_id=user_id,
            select_date=today
        ).first()
        
        if not cleaned_data:
            # 오늘 데이터 생성 시도
            success, cleaned_text = self.clean_daily_data(user_id, today)
            if not success:
                # 어제 데이터 확인
                yesterday = today - timedelta(days=1)
                cleaned_data = CleanedData.query.filter_by(
                    user_id=user_id,
                    select_date=yesterday
                ).first()
                
                if not cleaned_data:
                    # 어제 데이터 생성 시도
                    success, cleaned_text = self.clean_daily_data(user_id, yesterday)
                    if not success:
                        return False, "최소 하루의 데이터가 필요합니다."
                else:
                    cleaned_text = cleaned_data.cleaned_text
                    
                context = f"어제의 데이터:\n{cleaned_text}\n\n질문: {question}"
            else:
                context = f"오늘의 데이터:\n{cleaned_text}\n\n질문: {question}"
        else:
            cleaned_text = cleaned_data.cleaned_text
            context = f"오늘의 데이터:\n{cleaned_text}\n\n질문: {question}"
        
        system_prompt = """
        당신은 사용자의 일상을 관리해주는 AI 비서입니다.
        사용자의 일기, 할 일, 일정 데이터를 기반으로 자연스럽게 대화하며 도움을 제공해주세요.
        항상 친절하고 공감적인 태도를 유지하면서, 실질적인 도움이 되는 답변을 제공해주세요.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ]
        
        response = self.llm.predict_messages(messages)
        return True, response.content

    def create_feedback(self, user_id: int, select_date: datetime.date) -> Tuple[bool, str]:
        """일일 피드백 생성"""
        self._init_model()
        
        # CleanedData 조회
        cleaned_data = CleanedData.query.filter_by(
            user_id=user_id,
            select_date=select_date
        ).first()
        
        if not cleaned_data:
            # 오늘 데이터 생성 시도
            success, cleaned_text = self.clean_daily_data(user_id, select_date)
            if not success:
                # 어제 데이터 확인
                yesterday = select_date - timedelta(days=1)
                cleaned_data = CleanedData.query.filter_by(
                    user_id=user_id,
                    select_date=yesterday
                ).first()
                
                if not cleaned_data:
                    # 어제 데이터 생성 시도
                    success, cleaned_text = self.clean_daily_data(user_id, yesterday)
                    if not success:
                        return False, "최소 하루의 데이터가 필요합니다."
                else:
                    cleaned_text = cleaned_data.cleaned_text
                    
                context = f"어제의 데이터를 기반으로 피드백을 생성합니다:\n{cleaned_text}"
                use_date = yesterday
            else:
                context = f"오늘의 데이터를 기반으로 피드백을 생성합니다:\n{cleaned_text}"
                use_date = select_date
        else:
            cleaned_text = cleaned_data.cleaned_text
            context = f"오늘의 데이터를 기반으로 피드백을 생성합니다:\n{cleaned_text}"
            use_date = select_date
        
        system_prompt = """
        사용자의 하루 데이터를 분석하여 다음과 같은 피드백을 제공해주세요:
        1. 할 일 완료율과 성취도 분석
        2. 일정 관리의 효율성 평가
        3. 긍정적인 부분 강조
        4. 개선이 필요한 부분에 대한 건설적인 제안
        5. 전반적인 하루 평가와 격려의 메시지
        
        피드백은 항상 긍정적이고 동기부여가 되는 톤을 유지하면서, 구체적이고 실천 가능한 제안을 포함해야 합니다.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ]
        
        response = self.llm.predict_messages(messages)
        feedback_text = response.content
        
        # Feedback 모델에 저장
        feedback = Feedback(
            user_id=user_id,
            feedback=feedback_text,
            select_date=use_date
        )
        db.session.add(feedback)
        db.session.commit()
        
        return True, feedback_text

    def create_recommendation(self, user_id: int) -> Tuple[bool, str]:
        """일정 추천 생성"""
        self._init_model()
        
        # 오늘 날짜로 CleanedData 조회
        today = datetime.now().date()
        cleaned_data = CleanedData.query.filter_by(
            user_id=user_id,
            select_date=today
        ).first()
        
        if not cleaned_data:
            # 오늘 데이터 생성 시도
            success, cleaned_text = self.clean_daily_data(user_id, today)
            if not success:
                # 어제 데이터 확인
                yesterday = today - timedelta(days=1)
                cleaned_data = CleanedData.query.filter_by(
                    user_id=user_id,
                    select_date=yesterday
                ).first()
                
                if not cleaned_data:
                    # 어제 데이터 생성 시도
                    success, cleaned_text = self.clean_daily_data(user_id, yesterday)
                    if not success:
                        return False, "최소 하루의 데이터가 필요합니다."
                else:
                    cleaned_text = cleaned_data.cleaned_text
                    
                context = f"어제의 데이터를 기반으로 추천을 생성합니다:\n{cleaned_text}"
            else:
                context = f"오늘의 데이터를 기반으로 추천을 생성합니다:\n{cleaned_text}"
        else:
            cleaned_text = cleaned_data.cleaned_text
            context = f"오늘의 데이터를 기반으로 추천을 생성합니다:\n{cleaned_text}"
        
        system_prompt = """
        사용자의 하루 데이터를 분석하여 다음과 같은 추천을 제공해주세요:
        1. 현재 일정과 할 일을 고려한 시간 관리 제안
        2. 업무/학습 효율을 높일 수 있는 활동 추천
        3. 스트레스 해소와 휴식을 위한 활동 제안
        4. 사용자의 관심사와 목표를 고려한 새로운 활동 추천
        5. 건강과 웰빙을 위한 제안
        
        추천은 구체적이고 실천 가능해야 하며, 사용자의 현재 상황과 일정을 고려하여 제시되어야 합니다.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ]
        
        response = self.llm.predict_messages(messages)
        return True, response.content

    def _preprocess_text(self, text: str) -> str:
        """LLM을 사용한 텍스트 전처리"""
        system_prompt = """
        주어진 텍스트를 다음과 같이 전처리하세요:
        1. 불필요한 특수문자나 중복된 공백 제거
        2. 문장을 자연스럽게 연결
        3. 중요한 정보는 유지하면서 간결하게 정리
        4. 시간순으로 정리
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=text)
        ]
        
        response = self.llm.predict_messages(messages)
        return response.content