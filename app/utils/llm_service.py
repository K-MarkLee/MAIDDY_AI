from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from app.utils.chatbot_func import ChatbotFunction
from app.models import User, Schedule, Todo, Summary, Diary, AiResponse, Embedding
from sqlalchemy import and_
import os
from datetime import datetime, date, timedelta
import json
import numpy as np

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 시스템 프롬프트 설정
SYSTEM_PROMPT = """안녕하세요! 저는 MAIDDY예요! ✨
당신의 일상을 함께하는 작은 요정 비서랍니다! 🧚‍♀️

제가 도와드릴 수 있는 일들이에요:
🌟 소중한 일정 관리
🎯 즐거운 할일 체크
📝 특별한 일기 작성
💝 따뜻한 피드백과 추천

항상 밝고 귀엽게, 하지만 프로페셔널하게 도와드릴게요!
함께 즐거운 하루를 만들어보아요! 💕"""

class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7
        )
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.memory = ConversationBufferMemory()
        self.chatbot_func = ChatbotFunction(self.llm)
        self.last_memory_cleanup = datetime.now().date()

    def cleanup_memory(self):
        """하루가 지나면 대화 기록을 정리하는 메서드"""
        current_date = datetime.now().date()
        if current_date > self.last_memory_cleanup:
            self.memory.clear()
            self.last_memory_cleanup = current_date

    def get_user_name(self, user_id: int) -> str:
        """사용자 이름을 가져오는 메서드"""
        user = User.query.get(user_id)
        return user.username if user else "친구"

    def get_context_data(self, user_id: int, current_date: date) -> str:
        """사용자의 과거 데이터를 가져오는 메서드"""
        try:
            # 일정 데이터 가져오기
            schedules = Schedule.query.filter(
                Schedule.user_id == user_id,
                Schedule.select_date <= current_date
            ).order_by(Schedule.select_date.desc()).limit(5).all()
            
            # 할일 데이터 가져오기
            todos = Todo.query.filter(
                Todo.user_id == user_id,
                Todo.select_date <= current_date
            ).order_by(Todo.select_date.desc()).limit(5).all()
            
            context = []
            if schedules:
                schedule_text = "✨ 최근 일정:\n" + "\n".join([
                    f"🌟 {s.select_date} - {s.title} ({s.time})" 
                    for s in schedules
                ])
                context.append(schedule_text)
            
            if todos:
                todo_text = "✨ 최근 할일:\n" + "\n".join([
                    f"🎯 {t.select_date} - {t.content}"
                    for t in todos
                ])
                context.append(todo_text)
            
            return "\n\n".join(context)
        except Exception as e:
            return f"앗! 데이터를 가져오는 중에 문제가 생겼어요 😢: {str(e)}"

    def get_chat_response(self, user_id: int, question: str):
        """사용자의 질문에 대한 응답을 생성하는 메서드"""
        # 메모리 정리 체크
        self.cleanup_memory()
        
        username = self.get_user_name(user_id)
        
        # 사용자의 과거 데이터 확인
        current_date = datetime.now().date()
        context_data = self.get_context_data(user_id, current_date)
        has_past_data = bool(context_data.strip())
        
        # 일정 또는 할일 관련 요청인지 확인
        is_schedule_request = any(keyword in question.lower() for keyword in ["일정", "schedule", "약속"])
        is_todo_request = any(keyword in question.lower() for keyword in ["할일", "todo", "해야할", "해야 할"])
        
        # 요청 유형 확인
        is_add_request = any(keyword in question.lower() for keyword in ["추가", "등록", "만들어", "잡아", "넣어"])
        is_update_request = any(keyword in question.lower() for keyword in ["수정", "변경", "바꿔", "업데이트"])
        is_delete_request = any(keyword in question.lower() for keyword in ["삭제", "제거", "지워", "취소"])
        
        # 일정/할일 추가 요청 처리
        if is_add_request and (is_schedule_request or is_todo_request):
            if is_schedule_request:
                schedule_info = self.chatbot_func.extract_schedule_info(question)
                if schedule_info:
                    success, message = self.chatbot_func.add_schedule(user_id, schedule_info)
                    return message
                else:
                    return (
                        "앗! 일정 정보를 정확히 이해하지 못했어요 😅\n"
                        "이렇게 말씀해 주시면 더 잘 이해할 수 있을 것 같아요:\n"
                        "✨ '내일 오후 2시에 병원 예약이 있어'\n"
                        "✨ '다음 주 월요일 아침 9시에 팀 미팅 일정 추가해줘'"
                    )
            elif is_todo_request:
                todo_info = self.chatbot_func.extract_todo_info(question)
                if todo_info:
                    success, message = self.chatbot_func.add_todo(user_id, todo_info)
                    return message
                else:
                    return (
                        "앗! 할일 정보를 정확히 이해하지 못했어요 😅\n"
                        "이렇게 말씀해 주시면 더 잘 이해할 수 있을 것 같아요:\n"
                        "✨ '내일까지 보고서 작성하기'\n"
                        "✨ '오늘 할일로 이메일 답장하기 추가해줘'"
                    )
        
        # 일정/할일 수정 요청 처리
        elif is_update_request and (is_schedule_request or is_todo_request):
            if is_schedule_request:
                schedule, error_message = self.chatbot_func.find_schedule(user_id, question)
                if schedule:
                    schedule_info = self.chatbot_func.extract_schedule_info(question)
                    if schedule_info:
                        success, message = self.chatbot_func.update_schedule(user_id, schedule.id, schedule_info)
                        return message
                    else:
                        return (
                            "앗! 수정할 일정 정보를 정확히 이해하지 못했어요 😅\n"
                            "이렇게 말씀해 주시면 더 잘 이해할 수 있을 것 같아요:\n"
                            "✨ '오늘 2시 병원 예약을 3시로 변경해줘'\n"
                            "✨ '내일 팀 미팅 시간을 오후 2시로 수정해줘'"
                        )
                else:
                    return error_message
            elif is_todo_request:
                todo, error_message = self.chatbot_func.find_todo(user_id, question)
                if todo:
                    todo_info = self.chatbot_func.extract_todo_info(question)
                    if todo_info:
                        success, message = self.chatbot_func.update_todo(user_id, todo.id, todo_info)
                        return message
                    else:
                        return (
                            "앗! 수정할 할일 정보를 정확히 이해하지 못했어요 😅\n"
                            "이렇게 말씀해 주시면 더 잘 이해할 수 있을 것 같아요:\n"
                            "✨ '보고서 작성 마감일을 다음주로 변경해줘'\n"
                            "✨ '이메일 답장 할일을 내일로 미뤄줘'"
                        )
                else:
                    return error_message
        
        # 일반적인 대화인지 확인
        general_conversation = not any(keyword in question.lower() for keyword in [
            "일정", "할일", "todo", "schedule", "diary", "일기", 
            "피드백", "feedback", "recommend", "추천"
        ])
        
        if general_conversation:
            return (
                f"{username}님, 안녕하세요! 저는 요정 비서 MAIDDY예요! ✨\n"
                "제가 도와드릴 수 있는 일들을 소개해드릴게요:\n\n"
                "🌟 일정이나 할일을 추가하고 관리해드려요\n"
                "📝 소중한 일기도 함께 써요\n"
                "💝 당신의 하루를 더 특별하게 만들어드릴게요\n"
                "✨ 생산성 향상을 위한 귀여운 조언도 해드려요\n\n"
                "어떤 것을 도와드릴까요? 😊"
            )
        
        # 관련 데이터 검색
        similar_texts = self.get_similar_texts(question, user_id)
        historical_context = "\n\n".join([text for text, _ in similar_texts]) if similar_texts else ""
        
        if has_past_data:
            # 기존 사용자용 프롬프트
            chat_prompt = PromptTemplate(
                input_variables=["system_prompt", "username", "context", "question"],
                template=(
                    "{system_prompt}\n\n"
                    "소중한 {username}님의 과거 데이터를 바탕으로 답변드릴게요! ✨\n"
                    "컨텍스트: {context}\n\n"
                    "질문: {question}"
                )
            )
        else:
            # 첫 사용자용 프롬프트
            chat_prompt = PromptTemplate(
                input_variables=["system_prompt", "username", "question"],
                template=(
                    "{system_prompt}\n\n"
                    "와아! {username}님과 함께하는 첫 날이네요! 🎉\n"
                    "지금은 일정과 할일 추가를 도와드릴 수 있어요!\n"
                    "더 많은 추억을 쌓으면서 더 다양한 방법으로 도와드릴 수 있을 거예요! ✨\n\n"
                    "질문: {question}\n\n"
                    "어떤 일정이나 할일을 함께 기록해볼까요? 💝"
                )
            )
        
        # 응답 생성
        chain = ConversationChain(
            llm=self.llm,
            prompt=chat_prompt,
            memory=self.memory
        )
        
        if has_past_data:
            response = chain.predict(
                system_prompt=SYSTEM_PROMPT,
                username=username,
                context=context_data + "\n\n과거 기록:\n" + historical_context,
                question=question
            )
        else:
            response = chain.predict(
                system_prompt=SYSTEM_PROMPT,
                username=username,
                question=question
            )
        
        return response

    def collect_user_data(self, user_id: int, select_date: date) -> tuple[str, dict]:
        """사용자의 일기, 일정, 할일 데이터를 수집하고 하나의 텍스트로 통합하는 메서드"""
        try:
            # 해당 날짜의 데이터 수집
            schedules = Schedule.query.filter(
                Schedule.user_id == user_id,
                Schedule.select_date == select_date
            ).all()
            
            todos = Todo.query.filter(
                Todo.user_id == user_id,
                Todo.select_date == select_date
            ).all()
            
            diary = Diary.query.filter(
                Diary.user_id == user_id,
                Diary.select_date == select_date
            ).first()
            
            # 데이터 통합
            data_parts = []
            raw_data = {
                "schedules": [],
                "todos": [],
                "diary": None
            }
            
            if schedules:
                schedule_text = "✨ 오늘의 일정:\n" + "\n".join([
                    f"🌟 {s.time} - {s.title}" + (f" ({s.content})" if s.content else "")
                    for s in schedules
                ])
                data_parts.append(schedule_text)
                raw_data["schedules"] = [
                    {"time": s.time, "title": s.title, "content": s.content}
                    for s in schedules
                ]
            
            if todos:
                todo_text = "✨ 오늘의 할일:\n" + "\n".join([
                    f"🎯 {t.content}" + (" (완료)" if t.is_completed else "")
                    for t in todos
                ])
                data_parts.append(todo_text)
                raw_data["todos"] = [
                    {"content": t.content, "is_completed": t.is_completed}
                    for t in todos
                ]
            
            if diary:
                diary_text = f"✨ 오늘의 일기:\n📝 {diary.content}"
                data_parts.append(diary_text)
                raw_data["diary"] = {"content": diary.content}
            
            combined_text = "\n\n".join(data_parts) if data_parts else "오늘은 기록된 데이터가 없어요 😊"
            return combined_text, raw_data
            
        except Exception as e:
            return f"앗! 데이터를 수집하는 중에 문제가 생겼어요 😢: {str(e)}", {}

    def save_summary(self, user_id: int, summary_text: str, summary_type: str, select_date: date):
        """생성된 요약을 데이터베이스에 저장하는 메서드"""
        try:
            # 요약 저장
            summary = Summary(
                user_id=user_id,
                summary_text=summary_text,
                type=summary_type,
                select_date=select_date
            )
            db.session.add(summary)
            
            # 벡터 임베딩 생성 및 저장
            embedding_vector = self.embeddings.embed_query(summary_text)
            
            embedding = Embedding(
                user_id=user_id,
                text=summary_text,
                embedding=embedding_vector,
                metadata={
                    "type": summary_type,
                    "date": select_date.isoformat()
                }
            )
            db.session.add(embedding)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"앗! 요약을 저장하는 중에 문제가 생겼어요 😢: {str(e)}")

    def get_similar_texts(self, query: str, user_id: int, limit: int = 5):
        """유사한 텍스트를 검색하는 메서드"""
        try:
            # 쿼리 벡터 생성
            query_vector = self.embeddings.embed_query(query)
            
            # PostgreSQL의 벡터 유사도 검색 쿼리
            similar_embeddings = Embedding.query.filter(
                Embedding.user_id == user_id
            ).order_by(
                Embedding.embedding.cosine_distance(query_vector)
            ).limit(limit).all()
            
            return [(embed.text, embed.metadata) for embed in similar_embeddings]
            
        except Exception as e:
            print(f"유사 텍스트 검색 중 오류 발생: {str(e)}")
            return []

    def summarize_data(self, user_id: int, select_date: date) -> str:
        """하루의 데이터를 요약하는 메서드"""
        try:
            # 데이터 수집
            combined_text, _ = self.collect_user_data(user_id, select_date)
            
            if "기록된 데이터가 없어요" in combined_text:
                return "오늘은 특별한 활동이 없었네요! 내일은 어떤 즐거운 일들이 기다리고 있을까요? ✨"
            
            # 요약 프롬프트
            prompt = PromptTemplate(
                input_variables=["text"],
                template=(
                    "다음은 하루 동안의 활동 기록이에요:\n"
                    "{text}\n\n"
                    "이 내용을 귀엽고 따뜻한 톤으로 요약해주세요! 🌟\n"
                    "중요한 일정이나 할일은 반드시 포함해주시고,\n"
                    "일기의 감정이나 생각도 잘 반영해주세요! 💝"
                )
            )
            
            chain = ConversationChain(
                llm=self.llm,
                prompt=prompt,
                memory=None  # 요약에는 대화 기록이 필요 없어요
            )
            
            summary = chain.predict(text=combined_text)
            return summary
            
        except Exception as e:
            return f"앗! 요약하는 중에 문제가 생겼어요 😢: {str(e)}"

    def generate_daily_feedback(self, user_id: int, select_date: date) -> str:
        """하루 동안의 활동에 대한 피드백을 생성하는 메서드"""
        try:
            # 데이터 수집
            combined_text, raw_data = self.collect_user_data(user_id, select_date)
            
            if "기록된 데이터가 없어요" in combined_text:
                return "오늘은 조용한 하루였네요! 내일은 어떤 특별한 일들을 함께 기록해볼까요? ✨"
            
            # 피드백 프롬프트
            prompt = PromptTemplate(
                input_variables=["text"],
                template=(
                    "다음은 하루 동안의 활동 기록이에요:\n"
                    "{text}\n\n"
                    "이 내용을 바탕으로 다음과 같은 피드백을 제공해주세요:\n"
                    "1. 오늘의 성과와 긍정적인 부분 칭찬하기 🌟\n"
                    "2. 개선할 수 있는 부분 귀엽게 제안하기 💝\n"
                    "3. 내일을 위한 따뜻한 응원 한마디 ✨\n\n"
                    "귀엽고 친근한 톤으로 작성해주세요!"
                )
            )
            
            chain = ConversationChain(
                llm=self.llm,
                prompt=prompt,
                memory=None  # 피드백에는 대화 기록이 필요 없어요
            )
            
            feedback = chain.predict(text=combined_text)
            
            # 피드백 저장
            response = AiResponse(
                user_id=user_id,
                content=feedback,
                type="feedback",
                select_date=select_date
            )
            db.session.add(response)
            db.session.commit()
            
            return feedback
            
        except Exception as e:
            return f"앗! 피드백을 생성하는 중에 문제가 생겼어요 😢: {str(e)}"

    def recommend_schedule(self, user_id: int):
        """사용자의 패턴을 분석하여 일정을 추천하는 메서드"""
        username = self.get_user_name(user_id)
        current_date = datetime.now().date()
        context_data = self.get_context_data(user_id, current_date)
        
        recommend_prompt = PromptTemplate(
            input_variables=["system_prompt", "username", "context"],
            template="{system_prompt}\n\n{username}님, 다음은 귀하의 과거 활동 기록입니다:\n{context}\n\n"
            "내일의 일정과 할일을 추천해드리겠습니다. 다음 사항을 고려했습니다:\n"
            "1. 과거의 생산적인 패턴 유지\n"
            "2. 반복되는 일정 패턴\n"
            "3. 미완료된 할일의 적절한 배치\n"
            "4. 업무와 휴식의 균형\n"
            "구체적인 시간대와 함께 추천해드리겠습니다."
        )
        
        chain = ConversationChain(
            llm=self.llm,
            prompt=recommend_prompt,
            memory=self.memory
        )
        
        recommendations = chain.predict(
            system_prompt=SYSTEM_PROMPT,
            username=username,
            context=context_data
        )
        
        return recommendations