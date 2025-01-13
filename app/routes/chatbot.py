from flask import Blueprint, request, jsonify, current_app
from app.utils.llm_service import LLMService
from app.utils.save_response import save_ai_response
from app.models import Schedule, AiResponse, User, Todo, Summary
from app.database import db
from datetime import datetime
import re
import json


chatbot_bp = Blueprint("chatbot_bp", __name__)
llm_service = LLMService()


@chatbot_bp.route("/chatbot", methods=["POST"])
def chatbot():
    """
    사용자로부터 user_id 와 prompt를 받아서 LLM을 통해 답변을 생성 (일정 추가와 같은 기능 가능)
    """
    
    data = request.json or {}
    user_id = data.get("user_id")
    query = data.get("query")

    current_app.logger.info(f" {user_id} 유저의 질문을 받았습니다. 질문 : {query}")

    if not user_id or not query:
        current_app.logger.warning("유저 아이디 또는 프롬프트가 없습니다")
        return jsonify({"error": "유저 아이디 또는 프롬프트가 없습니다"}), 400
    
    user = User.query.filter_by(id=user_id).first()
    if not user:
        current_app.logger.waring(f"존재하지 않는 유저입니다. user_id: {user_id}")
        return jsonify({"error": "존재하지 않는 유저입니다"}), 400
    

    # 사용자 요약 데이터 수집
    recent_summaries = Summary.query.filter(
        Summary.user_id == user_id
    ).order_by(Summary.select_date.desc()).all()
    summary_texts = [summary.text for summary in recent_summaries]
    combined_summary = "\n".join(summary_texts)
    

    # LLM을 사용하여 명령어 파악 및 응답 생성
    prompt = f"""
    당신은 일정 및 할일 관리 챗봇입니다. 사용자의 질문을 분석하여 일정 또는 할일과 관련된 명령어를 파악하고, 필요한 경우 명령어를 처리하세요.
    사용자의 과거 요약: {combined_summary}
    사용자의 입력: "{query}"
    응답 형식:
    - 타입: [대화/명령어]
    - 응답: [챗봇의 답변]
    - 데이터: [JSON 형식의 추가 데이터]
    명령어 예시:
    - 일정 추가: {{"action": "add_schedule", "title": "회의", "time": "오후 7시", "select_date": "내일"}}
    - 일정 수정: {{"action": "update_schedule", "schedule_id": 1, "title": "회의 수정", "time": "오후 8시"}}
    - 일정 삭제: {{"action": "delete_schedule", "schedule_id": 1}}
    - 할일 추가: {{"action": "add_todo", "content": "책 읽기"}}
    - 할일 수정: {{"action": "update_todo", "todo_id": 2, "is_completed": true}}
    - 할일 삭제: {{"action": "delete_todo", "todo_id": 2}}
    - 할일 미완료 조회: {{"action": "query_incomplete_todo", "date": "어제"}}
    """

    llm_response = llm_service.generate_direct_response(prompt)
    current_app.logger.info(f"LLM 응답: {llm_response}")


    # 응답 파싱
    match = re.search(r"타입: (.+)\n- 응답: (.+)\n- 데이터: (.+)", llm_response, re.DOTALL)    
    if match:
        response_type = match.group(1).strip()
        response = match.group(2).strip()
        data_json = match.group(3).strip()
    else:
        # 기본적으로 일반 질문으로 처리
        response_type = "대화"
        response = llm_response.strip()
        data_json = "{}"

    current_app.logger.info(f"응답 타입: {response_type}, 응답: {response}, 데이터: {data_json}")


   # 명령어 처리
    if response_type.lower() == "명령어":
        try:
            # 추가 데이터 JSON 파싱
            data_dict = json.loads(data_json)
            action = data_dict.get("action")
            
            if action == "add_schedule":
                title = data_dict.get("title")
                content = data_dict.get("content", "")
                time = data_dict.get("time")
                select_date = data_dict.get("select_date")
                
                time = convert_time_str_to_24(time)
                select_date = parse_select_date(select_date)
                
                new_schedule = Schedule(
                    user_id=user_id,
                    title=title,
                    content=content,
                    time=time,
                    select_date=select_date
                )
                db.session.add(new_schedule)
                db.session.commit()
                response = f"일정이 성공적으로 추가되었습니다: {title} at {time} on {select_date.strftime('%Y-%m-%d')}"
                current_app.logger.info(f"{user_id}유저의 일정이 생성되었습니다.: {title} at {time} on {select_date}")
            
            elif action == "update_schedule":
                schedule_id = data_dict.get("schedule_id")
                title = data_dict.get("title")
                time = data_dict.get("time")
                
                schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
                if not schedule:
                    response = f"일정 ID {schedule_id}를 찾을 수 없습니다."
                else:
                    schedule.title = title if title else schedule.title
                    schedule.time = convert_time_str_to_24(time) if time else schedule.time
                    db.session.commit()
                    response = f"일정이 성공적으로 수정되었습니다: {schedule.title} at {schedule.time} on {schedule.date.strftime('%Y-%m-%d')}"
                    current_app.logger.info(f"{user_id}유저의 일정이 수정되었습니다.: {schedule.title} at {schedule.time} on {schedule.date}")
            
            elif action == "delete_schedule":
                schedule_id = data_dict.get("schedule_id")
                schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
                if not schedule:
                    response = f"일정 ID {schedule_id}를 찾을 수 없습니다."
                else:
                    db.session.delete(schedule)
                    db.session.commit()
                    response = f"일정 ID {schedule_id}가 삭제되었습니다."
                    current_app.logger.info(f"{user_id}유저의 일정이 삭제되었습니다.: ID {schedule_id}")
            
            elif action == "add_todo":
                task = data_dict.get("task")
                new_todo = Todo(
                    user_id=user_id,
                    content = content,
                    is_completed=False,
                    date=datetime.today().date()
                )
                db.session.add(new_todo)
                db.session.commit()
                response = f"할일이 성공적으로 추가되었습니다: {task}"
                current_app.logger.info(f"{user_id}유저의 할일이 추가되었습니다.: {task}")
            
            elif action == "update_todo":
                todo_id = data_dict.get("todo_id")
                is_completed = data_dict.get("is_completed")
                
                todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
                if not todo:
                    response = f"할일 ID {todo_id}를 찾을 수 없습니다."
                else:
                    todo.is_completed = is_completed
                    db.session.commit()
                    status = "완료" if is_completed else "미완료"
                    response = f"할일 ID {todo_id}가 {status}로 업데이트되었습니다."
                    current_app.logger.info(f" {user_id}유저의 할일 상태가 업데이트 되었습니다. : ID {todo_id}, Completed: {is_completed}")
            
            elif action == "delete_todo":
                todo_id = data_dict.get("todo_id")
                todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
                if not todo:
                    response = f"할일 ID {todo_id}를 찾을 수 없습니다."
                else:
                    db.session.delete(todo)
                    db.session.commit()
                    response = f"할일 ID {todo_id}가 삭제되었습니다."
                    current_app.logger.info(f"{user_id}유저의 할일이 삭제되었습니다. : ID {todo_id}")
            
            elif action == "query_incomplete_todo":
                date = data_dict.get("date")  # 예: "어제"
                query_date = parse_select_date(date)
                
                incomplete_todos = Todo.query.filter_by(user_id=user_id, is_completed=False, date=query_date).all()
                if not incomplete_todos:
                    response = f"{query_date.strftime('%Y-%m-%d')}에 완료하지 못한 할일이 없습니다."
                else:
                    todo_list = "\n".join([f"- {todo.task} (ID: {todo.id})" for todo in incomplete_todos])
                    response = f"{query_date.strftime('%Y-%m-%d')}에 완료하지 못한 할일 목록:\n{todo_list}"
                    current_app.logger.info(f"Incomplete todos queried for user {user_id} on {query_date}: {todo_list}")
            
            else:
                response = "알 수 없는 명령어입니다."
                current_app.logger.warning(f"Unknown action: {action}")
        
        except Exception as e:
            response = f"명령어 처리 중 오류가 발생했습니다: {str(e)}"
            current_app.logger.error(f"Command processing error for user {user_id}: {e}")

    elif response_type.lower() == "대화":
        # 대화 관련 응답 생성
        recent_responses = AiResponse.query.filter_by(user_id=user_id).order_by(AiResponse.created_at.desc()).limit(100).all()
        summaries = [resp.answer for resp in recent_responses]
        response = llm_service.generate_response(summaries, query)
        current_app.logger.info(f"Generated personalized response for user {user_id}")
    
    # AI 응답을 DB에 저장
    try:
        save_ai_response(user_id, query, response)
        current_app.logger.info(f"AI response saved for user {user_id}")
    except Exception as e:
        current_app.logger.error(f"Failed to save AI response for user {user_id}: {e}")
    
    return jsonify({"answer": response}), 200

def convert_time_str_to_24(time_str):
    """
    시간을 문자열에서 24시간 형식으로 변환합니다.
    예: '오후 7시' -> '19:00'
    
    :param time_str: 시간 문자열 (예: '오후 7시')
    :return: 24시간 형식의 시간 문자열 (예: '19:00')
    """
    import re
    match = re.match(r'(오전|오후)\s*(\d{1,2})시', time_str)
    if match:
        period = match.group(1)
        hour = int(match.group(2))
        if period == "오후" and hour != 12:
            hour += 12
        elif period == "오전" and hour == 12:
            hour = 0
        return f"{hour:02d}:00"
    return "00:00"  # 기본값

def parse_select_date(select_date_str):
    """
    선택된 날짜 문자열을 datetime.date 객체로 변환합니다.
    예: "어제" -> 오늘 -1일
    
    :param select_date_str: 날짜 문자열 (예: "어제", "내일", "2023-10-03")
    :return: datetime.date 객체
    """
    today = datetime.today().date()
    if select_date_str == "어제":
        return today - timedelta(days=1)
    elif select_date_str == "내일":
        return today + timedelta(days=1)
    elif select_date_str == "오늘":
        return today
    else:
        # YYYY-MM-DD 형식으로 입력된 경우
        try:
            return datetime.strptime(select_date_str, "%Y-%m-%d").date()
        except ValueError:
            return today  # 기본값