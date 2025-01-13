"""
APSscheduler 작업을 위한 별도 파일
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.llm_service import LLMService
from app.models import AiResponse, User, Summary
from app.database import db
from sqlalchemy import func
from datetime import datetime, timedelta
from flask import current_app


llm_service = LLMService()

def weekly_training():
    """
    매주 월요일 실행
    - 사용자의 요약 데이터 수집
    - Embedding 생성, LLM 학습, 업데이트
    """

    with db.session.no_autoflush:
        try:
            users = User.query.all()
            for user in users:

                # 사용자의 지난 주간 데이터수집
                one_week_ago = datetime.now() - timedelta(days=7)
                recent_responses = AiResponse.query.filter(
                    AiResponse.user_id == user.id,
                    AiResponse.select_date >= one_week_ago
                ).order_by(AiResponse.select_date.desc()).all()
                response_texts = [response.response for response in recent_responses]
                combined_responses = "\n".join(response_texts)


                # Summary 모델에서 지난 주간 요약 데이터 수집
                recent_summaries = Summary.query.filter(
                    Summary.user_id == user.id,
                    Summary.select_date >= one_week_ago
                ).order_by(Summary.select_date.desc()).all()
                summary_texts = [summary.summary_text for summary in recent_summaries]
                combined_summaries = "\n".join(summary_texts)

                # 두 데이터를 합침
                combined_text = combined_responses + "\n" + combined_summaries


                if combined_text.strip():
                    # Embedding 생성 및 VectorStore에 저장
                    embedding = llm_service.embed_text(combined_text)
                    llm_service.vector_store.add_texts(
                        texts=[combined_text],
                        ids=[str(user.id)],
                        embeddings=[embedding]
                    )
                    current_app.logger.info(f" {user.id}유저의 주간 학습 완료")
                    
                    # 학습한 데이터 삭제
                    for summary in recent_summaries:
                        db.session.delete(summary)
                    db.session.commit()
                    current_app.logger.info(f"Deleted processed data for user {user.id}")
        except Exception as e:
            current_app.logger.error(f"Weekly training task failed: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()

    # 매주 월요일 자정에 실행
    scheduler.add_job(func=weekly_training, trigger='cron', day_of_week='mon', hour=0, minute=0)
    scheduler.start()

    import atexit # 프로세스 종료시 스케줄러 종료
    atexit.register(lambda: scheduler.shutdown())