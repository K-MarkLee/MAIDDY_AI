from datetime import datetime
from app.models import Diary, Schedule, Todo, AiResponse
from app.utils.llm_service import LLMService


def retrieve_and_summarize(user_id: str, select_date: str) -> dict: # 유저 아이디와 날짜를 받아서 해당 날짜의 일기, 할일, 스케줄을 요약해서 반환
    try:
        select_date = datetime.strptime(select_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "날짜 형식이 잘못되었습니다. (YYYY-MM-DD)형식으로 입력해 주세요."}
    

    # DB에서 데이터 가져오기
    diaries = Diary.query.filter_by(user_id=user_id, date=select_date).all()
    todo = Todo.query.filter_by(user_id=user_id, date=select_date).all()
    schedules = Schedule.query.filter_by(user_id=user_id, date=select_date).all()


    # 각 항목의 콘텐츠 추출
    diary_contents = [diary.content for diary in diaries]
    todo_contents = [todo.content for todo in todo]
    schedule_contents = [schedule.content for schedule in schedules]
    schedule_titles = [schedule.title for schedule in schedules]

    llm_service = LLMService()

    # 텍스트 요약 및 키워드 추출
    summaries = {}


    if diary_contents:
        summaries['diaries'] = [llm_service.summarize_text(content) for content in diary_contents]
    else:
        summaries['diaries'] = []

    if todo_contents:
        summaries['todo'] = [llm_service.summarize_text(content) for content in todo_contents]
    else:
        summaries['todo'] = []

    if schedule_contents or schedule_titles:
        combined_schedules = [f"{title} {content}" for title, content in zip(schedule_titles, schedule_contents)]
        summaries['schedules'] = [llm_service.summarize_text(content) for content in combined_schedules]
    else:
        summaries['schedules'] = []

    return summaries



def retrieve_user_embeddings(user_id: str, limit: int = 100) -> list:
    """
    사용자의 최근 대화 내용을 가져와서 Embedding을 반환
    """
    recent_responses = AiResponse.query.filter_by(user_id=user_id).order_by(AiResponse.created_at.desc()).limit(limit).all()
    embeddings = [response.embedding for response in recent_responses if response.embedding is not None]
    return embeddings
