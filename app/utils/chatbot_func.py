from datetime import datetime
from app.extensions import db
from app.models import Schedule, Todo
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
import json

class ChatbotFunction:
    def __init__(self, llm):
        self.llm = llm

    def extract_schedule_info(self, text: str) -> dict:
        """
        텍스트에서 일정 정보를 추출하는 메서드
        """
        prompt = PromptTemplate(
            input_variables=["text"],
            template=(
                "다음 텍스트에서 일정 정보를 추출해주세요:\n"
                "{text}\n\n"
                "다음 형식의 JSON으로 응답해주세요:\n"
                "{\n"
                "  'title': '일정 제목',\n"
                "  'select_date': 'YYYY-MM-DD',\n"
                "  'time': 'HH:MM'\n"
                "}\n\n"
                "시간이 명시되지 않은 경우 '09:00'을 기본값으로 사용하세요."
            )
        )
        
        chain = ConversationChain(llm=self.llm, prompt=prompt)
        response = chain.predict(text=text)
        
        try:
            schedule_info = json.loads(response)
            return schedule_info
        except:
            return None

    def extract_todo_info(self, text: str) -> dict:
        """
        텍스트에서 할일 정보를 추출하는 메서드
        """
        prompt = PromptTemplate(
            input_variables=["text"],
            template=(
                "다음 텍스트에서 할일 정보를 추출해주세요:\n"
                "{text}\n\n"
                "다음 형식의 JSON으로 응답해주세요:\n"
                "{\n"
                "  'content': '할일 내용',\n"
                "  'select_date': 'YYYY-MM-DD'\n"
                "}\n\n"
                "날짜가 명시되지 않은 경우 오늘 날짜를 사용하세요."
            )
        )
        
        chain = ConversationChain(llm=self.llm, prompt=prompt)
        response = chain.predict(text=text)
        
        try:
            todo_info = json.loads(response)
            return todo_info
        except:
            return None

    def add_schedule(self, user_id: int, schedule_info: dict) -> tuple[bool, str]:
        """일정을 추가하는 메서드"""
        try:
            schedule = Schedule(
                user_id=user_id,
                title=schedule_info['title'],
                content=schedule_info.get('content'),
                select_date=schedule_info['select_date'],
                time=schedule_info['time']
            )
            db.session.add(schedule)
            db.session.commit()
            return True, f"✨ '{schedule.title}' 일정을 {schedule.select_date}에 추가했어요! 잊지 않도록 잘 기억해둘게요! 💝"
        except Exception as e:
            db.session.rollback()
            return False, f"앗.. 일정을 추가하다가 문제가 생겼어요 😢 다시 한 번 말씀해 주시겠어요? 오류: {str(e)}"

    def update_schedule(self, user_id: int, schedule_id: int, schedule_info: dict) -> tuple[bool, str]:
        """일정을 수정하는 메서드"""
        try:
            schedule = Schedule.query.filter_by(user_id=user_id, id=schedule_id).first()
            if not schedule:
                return False, "앗! 수정하려는 일정을 찾을 수 없어요 😅"
            
            schedule.title = schedule_info.get('title', schedule.title)
            schedule.content = schedule_info.get('content', schedule.content)
            schedule.select_date = schedule_info.get('select_date', schedule.select_date)
            schedule.time = schedule_info.get('time', schedule.time)
            
            db.session.commit()
            return True, f"✨ '{schedule.title}' 일정을 수정했어요! 변경된 내용으로 잘 기억해둘게요! 💫"
        except Exception as e:
            db.session.rollback()
            return False, f"앗.. 일정을 수정하다가 문제가 생겼어요 😢 다시 한 번 말씀해 주시겠어요? 오류: {str(e)}"

    def delete_schedule(self, user_id: int, schedule_id: int) -> tuple[bool, str]:
        """일정을 삭제하는 메서드"""
        try:
            schedule = Schedule.query.filter_by(user_id=user_id, id=schedule_id).first()
            if not schedule:
                return False, "앗! 삭제하려는 일정을 찾을 수 없어요 😅"
            
            title = schedule.title
            db.session.delete(schedule)
            db.session.commit()
            return True, f"✨ '{title}' 일정을 삭제했어요! 다른 일정이 있다면 언제든 말씀해 주세요! 💕"
        except Exception as e:
            db.session.rollback()
            return False, f"앗.. 일정을 삭제하다가 문제가 생겼어요 😢 다시 한 번 말씀해 주시겠어요? 오류: {str(e)}"

    def add_todo(self, user_id: int, todo_info: dict) -> tuple[bool, str]:
        """할일을 추가하는 메서드"""
        try:
            todo = Todo(
                user_id=user_id,
                content=todo_info['content'],
                select_date=todo_info['select_date']
            )
            db.session.add(todo)
            db.session.commit()
            return True, f"✨ '{todo.content}' 할일을 {todo.select_date}에 추가했어요! 잊지 않도록 잘 기억해둘게요! 💝"
        except Exception as e:
            db.session.rollback()
            return False, f"앗.. 할일을 추가하다가 문제가 생겼어요 😢 다시 한 번 말씀해 주시겠어요? 오류: {str(e)}"

    def update_todo(self, user_id: int, todo_id: int, todo_info: dict) -> tuple[bool, str]:
        """할일을 수정하는 메서드"""
        try:
            todo = Todo.query.filter_by(user_id=user_id, id=todo_id).first()
            if not todo:
                return False, "앗! 수정하려는 할일을 찾을 수 없어요 😅"
            
            todo.content = todo_info.get('content', todo.content)
            todo.select_date = todo_info.get('select_date', todo.select_date)
            
            db.session.commit()
            return True, f"✨ '{todo.content}' 할일을 수정했어요! 변경된 내용으로 잘 기억해둘게요! 💫"
        except Exception as e:
            db.session.rollback()
            return False, f"앗.. 할일을 수정하다가 문제가 생겼어요 😢 다시 한 번 말씀해 주시겠어요? 오류: {str(e)}"

    def delete_todo(self, user_id: int, todo_id: int) -> tuple[bool, str]:
        """할일을 삭제하는 메서드"""
        try:
            todo = Todo.query.filter_by(user_id=user_id, id=todo_id).first()
            if not todo:
                return False, "앗! 삭제하려는 할일을 찾을 수 없어요 😅"
            
            content = todo.content
            db.session.delete(todo)
            db.session.commit()
            return True, f"✨ '{content}' 할일을 삭제했어요! 다른 할일이 있다면 언제든 말씀해 주세요! 💕"
        except Exception as e:
            db.session.rollback()
            return False, f"앗.. 할일을 삭제하다가 문제가 생겼어요 😢 다시 한 번 말씀해 주시겠어요? 오류: {str(e)}"

    def find_schedule(self, user_id: int, text: str) -> tuple[Schedule, str]:
        """사용자의 텍스트에서 일정을 찾는 메서드"""
        prompt = PromptTemplate(
            input_variables=["text"],
            template=(
                "다음 텍스트에서 일정 검색에 필요한 정보를 추출해주세요:\n"
                "{text}\n\n"
                "다음 형식의 JSON으로 응답해주세요:\n"
                "{\n"
                "  'title': '일정 제목의 키워드',\n"
                "  'select_date': 'YYYY-MM-DD'\n"
                "}\n\n"
                "날짜가 명시되지 않은 경우 오늘 날짜를 사용하세요."
            )
        )
        
        chain = ConversationChain(llm=self.llm, prompt=prompt)
        response = chain.predict(text=text)
        
        try:
            search_info = json.loads(response)
            date = datetime.strptime(search_info['select_date'], '%Y-%m-%d').date()
            
            schedules = Schedule.query.filter(
                Schedule.user_id == user_id,
                Schedule.select_date == date,
                Schedule.title.ilike(f"%{search_info['title']}%")
            ).all()
            
            if not schedules:
                return None, f"앗! {search_info['select_date']}에 '{search_info['title']}'와 관련된 일정을 찾을 수 없어요 😅"
            elif len(schedules) > 1:
                schedule_list = "\n".join([f"✨ {s.title} ({s.time})" for s in schedules])
                return None, f"어머! 비슷한 일정이 여러 개 있네요! 🤔\n어떤 일정을 말씀하시는 건가요?\n{schedule_list}"
            else:
                return schedules[0], ""
        except:
            return None, "앗! 일정 검색에 필요한 정보를 이해하지 못했어요 😢 다시 한 번 말씀해 주시겠어요?"

    def find_todo(self, user_id: int, text: str) -> tuple[Todo, str]:
        """사용자의 텍스트에서 할일을 찾는 메서드"""
        prompt = PromptTemplate(
            input_variables=["text"],
            template=(
                "다음 텍스트에서 할일 검색에 필요한 정보를 추출해주세요:\n"
                "{text}\n\n"
                "다음 형식의 JSON으로 응답해주세요:\n"
                "{\n"
                "  'content': '할일 내용의 키워드',\n"
                "  'select_date': 'YYYY-MM-DD'\n"
                "}\n\n"
                "날짜가 명시되지 않은 경우 오늘 날짜를 사용하세요."
            )
        )
        
        chain = ConversationChain(llm=self.llm, prompt=prompt)
        response = chain.predict(text=text)
        
        try:
            search_info = json.loads(response)
            date = datetime.strptime(search_info['select_date'], '%Y-%m-%d').date()
            
            todos = Todo.query.filter(
                Todo.user_id == user_id,
                Todo.select_date == date,
                Todo.content.ilike(f"%{search_info['content']}%")
            ).all()
            
            if not todos:
                return None, f"앗! {search_info['select_date']}에 '{search_info['content']}'와 관련된 할일을 찾을 수 없어요 😅"
            elif len(todos) > 1:
                todo_list = "\n".join([f"✨ {t.content}" for t in todos])
                return None, f"어머! 비슷한 할일이 여러 개 있네요! 🤔\n어떤 할일을 말씀하시는 건가요?\n{todo_list}"
            else:
                return todos[0], ""
        except:
            return None, "앗! 할일 검색에 필요한 정보를 이해하지 못했어요 😢 다시 한 번 말씀해 주시겠어요?"
