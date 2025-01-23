from flask import jsonify, request, current_app
from app import db
from app.models import Schedule, Todo
from typing import Tuple

class ChatbotFunctions:
    def __init__(self):
        pass

    def process_chat(self, user_id: int, question: str):
        from app.utils.llm_service import LLMService

        llm_service = LLMService()
        date, time, content = None, None, question

        # 날짜와 시간 패턴 찾기
        if "내일" in question:
            date = "내일"
        elif "오늘" in question:
            date = "오늘"
        if "시" in question:
            time = question.split("시")[0].split()[-1]
            content = question.split("시")[-1].strip()

        # 날짜가 명시되지 않은 경우 기본 날짜 설정
        if not date:
            date = "오늘"

        if "할일 생성" in question:
            success, message = self.create_todo(user_id, content)
            return jsonify({'success': success, 'message': message})
        elif "할일 수정" in question:
            todo_id, content = map(str.strip, question.split("할일 수정 ")[-1].split("에 대해"))
            success, message = self.update_todo(user_id, int(todo_id), content)
            return jsonify({'success': success, 'message': message})
        elif "할일 삭제" in question:
            todo_id = question.split("할일 삭제 ")[-1]
            success, message = self.delete_todo(user_id, int(todo_id))
            return jsonify({'success': success, 'message': message})
        elif "일정 생성" in question:
            title = content
            success, message = self.create_schedule(user_id, title, content, date, time)
            return jsonify({'success': success, 'message': message})
        elif "일정 수정" in question:
            schedule_id, title, content = map(str.strip, question.split("일정 수정 ")[-1].split("에 대해"))
            success, message = self.update_schedule(user_id, int(schedule_id), title, content)
            return jsonify({'success': success, 'message': message})
        elif "일정 삭제" in question:
            schedule_id = question.split("일정 삭제 ")[-1]
            success, message = self.delete_schedule(user_id, int(schedule_id))
            return jsonify({'success': success, 'message': message})
        else:
            success, response = llm_service.get_chat_response(user_id, question)
            return jsonify({'success': success, 'response': response})

    def create_todo(self, user_id: int, content: str) -> Tuple[bool, str]:
        """할일 생성"""
        try:
            new_todo = Todo(user_id=user_id, content=content)
            db.session.add(new_todo)
            db.session.commit()
            return True, "할일이 생성되었습니다."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in create_todo: {str(e)}")
            return False, "할일 생성 중 오류가 발생했습니다."

    def update_todo(self, user_id: int, todo_id: int, content: str) -> Tuple[bool, str]:
        """할일 수정"""
        try:
            todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
            if not todo:
                return False, "할일을 찾을 수 없습니다."
            todo.content = content
            db.session.commit()
            return True, "할일이 수정되었습니다."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in update_todo: {str(e)}")
            return False, "할일 수정 중 오류가 발생했습니다."

    def delete_todo(self, user_id: int, todo_id: int) -> Tuple[bool, str]:
        """할일 삭제"""
        try:
            todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
            if not todo:
                return False, "할일을 찾을 수 없습니다."
            db.session.delete(todo)
            db.session.commit()
            return True, "할일이 삭제되었습니다."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in delete_todo: {str(e)}")
            return False, "할일 삭제 중 오류가 발생했습니다."

    def create_schedule(self, user_id: int, title: str, content: str, select_date: str, time: str) -> Tuple[bool, str]:
        """일정 생성"""
        try:
            new_schedule = Schedule(user_id=user_id, title=title, content=content, select_date=select_date, time=time)
            db.session.add(new_schedule)
            db.session.commit()
            return True, "일정이 생성되었습니다."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in create_schedule: {str(e)}")
            return False, "일정 생성 중 오류가 발생했습니다."

    def update_schedule(self, user_id: int, schedule_id: int, title: str, content: str) -> Tuple[bool, str]:
        """일정 수정"""
        try:
            schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
            if not schedule:
                return False, "일정을 찾을 수 없습니다."
            schedule.title = title
            schedule.content = content
            db.session.commit()
            return True, "일정이 수정되었습니다."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in update_schedule: {str(e)}")
            return False, "일정 수정 중 오류가 발생했습니다."

    def delete_schedule(self, user_id: int, schedule_id: int) -> Tuple[bool, str]:
        """일정 삭제"""
        try:
            schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
            if not schedule:
                return False, "일정을 찾을 수 없습니다."
            db.session.delete(schedule)
            db.session.commit()
            return True, "일정이 삭제되었습니다."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in delete_schedule: {str(e)}")
            return False, "일정 삭제 중 오류가 발생했습니다."
