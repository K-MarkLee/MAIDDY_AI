# app/utils/llm_service.py

from typing import List, Optional, Dict
from decouple import config
from app.models import UserPattern
from app.extensions import db
from flask import current_app
from datetime import datetime, timedelta
from app.models import Diary, Todo, Schedule, User
import json
import openai
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import LLMChain



    


# OpenAI API 키 설정
openai.api_key = config("OPENAI_API_KEY")

class LLMService:
    """
    LLM 서비스 클래스
    OpenAI API를 사용하여 요약, 임베딩 생성 및 개인화된 응답을 처리.
    """
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.7)
        self.output_parser = StrOutputParser()
        
        # 기본 시스템 프롬프트
        self.system_prompt = """
        당신은 사용자의 개인 AI 어시스턴트입니다. 다음과 같은 기능을 수행할 수 있습니다:
        1. 할일/일정 관리
        2. 과거 데이터 분석
        3. 패턴 기반 추천
        4. 개인화된 피드백
        5. 동기부여 대화

        사용자의 데이터를 기반으로 개인화된 대화를 나누되, 서비스 관련 내용에 집중해주세요.
        항상 긍정적이고 동기부여가 되는 방식으로 응답해주세요.
        """
        self.cache = {}  # 메모리 캐시

    async def chatbot(self, user_id: int, query: str) -> str:
        """메인 챗봇 인터페이스"""
        try:
            # 사용자 컨텍스트 수집
            user_context = await self._get_user_context(user_id)
            
            # 응답 생성
            response = await self._generate_chat_response(query, user_context)
            
            return response
            
        except Exception as e:
            current_app.logger.error(f"Chat processing error: {str(e)}")
            raise e

    async def generate_feedback(self, user_id: int, select_date: datetime.date) -> Dict:
        """일일 피드백 생성"""
        try:
            # 1. 해당 날짜 데이터 수집
            daily_data = await self._collect_daily_data(user_id, select_date)
            
            # 2. 패턴 데이터 조회
            user_pattern = await self._get_latest_pattern(user_id)
            
            # 3. 피드백 생성
            feedback_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""
                사용자의 하루를 분석하고 긍정적이면서도 실용적인 피드백을 제공해주세요:
                1. 오늘의 달성도
                2. 긍정적인 부분
                3. 개선 가능한 부분
                4. 내일을 위한 조언
                """),
                HumanMessage(content=f"""
                오늘의 데이터: {json.dumps(daily_data, ensure_ascii=False)}
                패턴 데이터: {json.dumps(user_pattern, ensure_ascii=False)}
                """)
            ])
            
            feedback_chain = LLMChain(llm=self.llm, prompt=feedback_prompt)
            feedback = await feedback_chain.arun()
            
            return {
                "feedback": feedback,
                "daily_data": daily_data,
                "patterns": user_pattern
            }

        except Exception as e:
            current_app.logger.error(f"피드백 생성 중 오류: {str(e)}")
            raise

    async def generate_recommendations(self, user_id: int) -> Dict:
        """패턴 기반 추천 생성"""
        try:
            # 1. 최신 패턴 데이터 조회
            latest_pattern = await self._get_latest_pattern(user_id)
            
            if not latest_pattern:
                # 패턴 데이터가 없으면 새로 분석
                await self.update_user_patterns(user_id)
                latest_pattern = await self._get_latest_pattern(user_id)

            # 2. 추천 생성
            recommendation_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""
                사용자의 패턴을 기반으로 개인화된 추천을 제공해주세요:
                1. 최적 시간대 추천
                2. 습관화 가능한 활동
                3. 구체적인 실천 방안
                4. 예상되는 긍정적 결과
                """),
                HumanMessage(content=f"""
                패턴 데이터: {json.dumps(latest_pattern, ensure_ascii=False)}
                """)
            ])
            
            recommendation_chain = LLMChain(llm=self.llm, prompt=recommendation_prompt)
            recommendations = await recommendation_chain.arun()
            
            return {
                "recommendations": recommendations,
                "patterns": latest_pattern
            }

        except Exception as e:
            current_app.logger.error(f"추천 생성 중 오류: {str(e)}")
            raise

    async def update_user_patterns(self, user_id: int) -> None:
        """사용자 패턴 분석 및 업데이트"""
        try:
            patterns = await self._analyze_comprehensive_patterns(user_id)
            
            today = datetime.now().date()
            user_pattern = UserPattern.query.filter_by(
                user_id=user_id,
                analyzed_date=today
            ).first()
            
            if not user_pattern:
                user_pattern = UserPattern(
                    user_id=user_id,
                    analyzed_date=today
                )
            
            user_pattern.activity_patterns = patterns["activity_patterns"]
            user_pattern.time_patterns = patterns["time_patterns"]
            user_pattern.success_patterns = patterns["success_patterns"]
            user_pattern.habit_streaks = patterns["habit_streaks"]
            
            db.session.add(user_pattern)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"패턴 업데이트 중 오류: {str(e)}")
            raise

    async def _analyze_comprehensive_patterns(self, user_id: int) -> Dict:
        """종합적인 사용자 패턴 분석"""
        try:
            three_months_ago = datetime.now() - timedelta(days=90)
            
            # 데이터 수집
            todos = Todo.query.filter(
                Todo.user_id == user_id,
                Todo.select_date >= three_months_ago
            ).all()
            
            schedules = Schedule.query.filter(
                Schedule.user_id == user_id,
                Schedule.select_date >= three_months_ago
            ).all()
            
            diaries = Diary.query.filter(
                Diary.user_id == user_id,
                Diary.select_date >= three_months_ago
            ).all()

            # 활동 패턴 분석
            activity_patterns = self._analyze_activities(todos, schedules)
            
            # 시간 패턴 분석
            time_patterns = self._analyze_time_patterns(schedules)
            
            # 성공 패턴 분석
            success_patterns = self._analyze_success_patterns(todos, schedules, diaries)
            
            # 습관 스트릭 분석
            habit_streaks = self._analyze_habit_streaks(todos, schedules)

            return {
                "activity_patterns": activity_patterns,
                "time_patterns": time_patterns,
                "success_patterns": success_patterns,
                "habit_streaks": habit_streaks
            }

        except Exception as e:
            current_app.logger.error(f"패턴 분석 중 오류: {str(e)}")
            raise

    async def _handle_data_action(self, user_id: int, intent_response: Dict) -> Dict:
        """데이터 생성/수정 처리"""
        try:
            intent = intent_response["intent"]
            data = intent_response["data"]
            
            if intent == "create_todo":
                todo = Todo(
                    user_id=user_id,
                    content=data["content"],
                    select_date=data.get("date", datetime.now().date())
                )
                db.session.add(todo)
                db.session.commit()
                return {"status": "success", "type": "todo", "action": "create", "id": todo.id}
                
            elif intent == "create_schedule":
                schedule = Schedule(
                    user_id=user_id,
                    content=data["content"],
                    time=data["time"],
                    select_date=data.get("date", datetime.now().date())
                )
                db.session.add(schedule)
                db.session.commit()
                return {"status": "success", "type": "schedule", "action": "create", "id": schedule.id}
                
            elif intent == "modify_todo":
                todo = Todo.query.get(data["item_id"])
                if todo and todo.user_id == user_id:
                    if "content" in data:
                        todo.content = data["content"]
                    db.session.commit()
                    return {"status": "success", "type": "todo", "action": "modify", "id": todo.id}
                    
            elif intent == "modify_schedule":
                schedule = Schedule.query.get(data["item_id"])
                if schedule and schedule.user_id == user_id:
                    if "content" in data:
                        schedule.content = data["content"]
                    if "time" in data:
                        schedule.time = data["time"]
                    db.session.commit()
                    return {"status": "success", "type": "schedule", "action": "modify", "id": schedule.id}
            
            return {"status": "error", "message": "Invalid action or data"}
            
        except Exception as e:
            db.session.rollback()
            raise

    # 헬퍼 메서드들
    def _analyze_activities(self, todos: List, schedules: List) -> Dict:
        """활동 패턴 분석"""
        activity_patterns = {}
        
        for todo in todos:
            content = todo.content
            if content not in activity_patterns:
                activity_patterns[content] = {"frequency": 1, "type": "todo"}
            else:
                activity_patterns[content]["frequency"] += 1

        for schedule in schedules:
            content = schedule.content
            if content not in activity_patterns:
                activity_patterns[content] = {"frequency": 1, "type": "schedule", "times": [schedule.time]}
            else:
                activity_patterns[content]["frequency"] += 1
                if "times" in activity_patterns[content]:
                    activity_patterns[content]["times"].append(schedule.time)

        return activity_patterns

    def _analyze_time_patterns(self, schedules: List) -> Dict:
        """시간 패턴 분석"""
        time_patterns = {
            "busy_hours": {},
            "free_hours": {},
            "preferred_times": {}
        }
        
        for schedule in schedules:
            hour = schedule.time.hour
            if hour not in time_patterns["busy_hours"]:
                time_patterns["busy_hours"][hour] = 1
            else:
                time_patterns["busy_hours"][hour] += 1

        return time_patterns

    async def _get_latest_pattern(self, user_id: int) -> Optional[Dict]:
        """최신 패턴 데이터 조회"""
        pattern = UserPattern.query.filter_by(user_id=user_id)\
            .order_by(UserPattern.analyzed_date.desc())\
            .first()
            
        if pattern:
            return {
                "activity_patterns": pattern.activity_patterns,
                "time_patterns": pattern.time_patterns,
                "success_patterns": pattern.success_patterns,
                "habit_streaks": pattern.habit_streaks
            }
        return None

    def analyze_user_patterns(self, user_id: int) -> Dict:
        # 캐시 키 생성
        cache_key = f"patterns_{user_id}_{datetime.now().date()}"
        
        # 캐시된 분석 결과가 있으면 반환
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # 없으면 새로 분석
        patterns = self._analyze_patterns(user_id)
        self.cache[cache_key] = patterns
        return patterns

    async def _analyze_intent(self, query: str) -> Dict:
        """사용자 의도 분석"""
        intent_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="사용자의 의도를 분석하여 다음 중 하나로 분류해주세요: create_todo, create_schedule, modify_todo, modify_schedule, general_chat"),
            HumanMessage(content=query)
        ])
        
        # LLMChain 대신 새로운 방식 사용
        chain = intent_prompt | self.llm | self.output_parser
        intent = await chain.ainvoke({"text": query})
        
        return {
            "intent": intent.strip().lower(),
            "data": {}
        }

    async def _get_user_context(self, user_id: int) -> Dict:
        """사용자 컨텍스트 수집"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}
                
            return {
                "name": user.username,
                "patterns": await self._get_latest_pattern(user_id)
            }
        except Exception as e:
            current_app.logger.error(f"Error getting user context: {str(e)}")
            return {}

    async def _generate_chat_response(self, query: str, user_context: Dict) -> str:
        """일반 대화 응답 생성"""
        chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""
            사용자 컨텍스트: {json.dumps(user_context, ensure_ascii=False)}
            사용자 질문: {query}
            """)
        ])
        
        # LLMChain 대신 새로운 방식 사용
        chain = chat_prompt | self.llm | self.output_parser
        response = await chain.ainvoke({"text": query})
        
        return response.strip()
    async def _generate_action_response(self, query: str, action_result: Dict, user_context: Dict) -> str:
        """작업 결과에 대한 응답 생성"""
        action_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""
            사용자 컨텍스트: {json.dumps(user_context, ensure_ascii=False)}
            사용자 요청: {query}
            작업 결과: {json.dumps(action_result, ensure_ascii=False)}
            
            작업 결과를 바탕으로 적절한 응답을 생성해주세요.
            """)
        ])
        
        action_chain = LLMChain(llm=self.llm, prompt=action_prompt)
        response = await action_chain.arun()
        
        return response.strip()

