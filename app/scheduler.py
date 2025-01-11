"""
APSscheduler 작업을 위한 별도 파일
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.llm_service import LLMService
from app.models import AiResponse, User
from app.database import db
from sqlalchemy import func

llm_service = LLMService()

def daily_training():
    """
    매일 자정 실행
    - 사용자의 요약 데이터 수집
    - Embedding 생성, LLM 학습, 업데이트
    """

    with db.session.no_autoflush:
        users = User.query.all()
        for user in users:
            recent_responses = AiResponse.query.filter_by(user_id=user.id).order_by(AiResponse.created_at.desc()).limit(100).all()
            summaries = [response.response for response in recent_responses]
            combined_summaries = "\n".join(summaries)


            # Embedding 생성
            embedding = llm_service.get_embedding(combined_summaries)

            # LLM 학습


            print(f"User {user.id} 학습 완료")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func = daily_training, trigger = "cron", hour = 0, minute = 0)
    scheduler.start()

    import atexit # 프로세스 종료시 스케줄러 종료
    atexit.register(lambda: scheduler.shutdown())