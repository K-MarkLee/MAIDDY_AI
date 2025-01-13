
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.llm_service import LLMService
from app.models import Summary, User
from app.database import db
from datetime import datetime, timedelta
from flask import current_app
from app.models import Diary, Todo, Schedule

llm_service = LLMService()

def daily_update():
    """
    매일 실행되는 작업:
    - 모든 사용자의 새로운 summaries 데이터를 수집
    - 요약 및 임베딩 생성 후 FAISS에 저장
    - summaries 데이터를 삭제
    """
    try:
        users = User.query.all()
        yesterday = datetime.now().date() - timedelta(days=1)

        for user in users:
            current_app.logger.info(f"{user.user_name}님의 {yesterday}의 요약 데이터를 처리합니다.")

            # 이미 피드백이 생성되었는지 확인(피드백이 생성되었으면 FAISS 업데이트가 이미 되었음.)
            feedback_summary = Summary.query.filter_by(
                user_id=user.id,
                select_date=yesterday,
                type="feedback"
            ).first()

            if feedback_summary:   
                current_app.logger.info(f"{user.user_name}님의 피드백 데이터가 있습니다. 처리하지 않습니다.")
                # Summary 삭제
                db.session.delete(feedback_summary)
                db.session.commit()
                continue  # 다음 사용자로 이동
                

            # 어제 날짜의 Diary, Todo, Schedule 데이터를 수집
            diaries = Diary.query.filter_by(user_id=user.id, select_date=yesterday).all()
            todo = Todo.query.filter_by(user_id=user.id, select_date=yesterday).all()
            schedules = Schedule.query.filter_by(user_id=user.id, select_date=yesterday).all()

            # 데이터 존재 여부 확인
            if not diaries and not todo and not schedules:
                current_app.logger.info(f"{user.user_name}의 {yesterday} 정보가 없습니다.")
                continue

            # 데이터 결합
            diary_texts = [diary.content for diary in diaries]
            todo_texts = [todo.content for todo in todo]
            schedule_texts = [f"{schedule.title}: {schedule.content}" for schedule in schedules]

            combined_text = "\n".join(diary_texts + todo_texts + schedule_texts)
            current_app.logger.debug(f"Combined text for {user.user_name}: {combined_text[:100]}...")  # 로그에 일부만 표시

            # llm_service를 사용하여 요약 생성 및 저장
            summary = llm_service.summarize_and_save(
                user_id=user.id,
                text=combined_text,
                data_type="feedback",
                select_date=yesterday
            )

            if summary:
                current_app.logger.info(f"{user.user_name}의 {yesterday}의 요약이 생성되었습니다.")

                # 처리한 Summary 데이터 삭제
                db.session.delete(summary)
                db.session.commit()
                current_app.logger.info(f"Summary ID {summary.id} for {user.user_name} has been deleted after embedding.")
            else:
                current_app.logger.error(f"Failed to create summary for {user.user_name} on {yesterday}.")
                
    except Exception as e:
        current_app.logger.error(f"Daily update task failed: {e}")

def start_scheduler(app):
    """
    스케줄러를 초기화하고, 주기적인 작업을 설정.
    
    :param app: Flask 애플리케이션 인스턴스
    """
    scheduler = BackgroundScheduler()
    # 매일 자정에 실행
    scheduler.add_job(func=daily_update, trigger='cron', day='*', hour=0, minute=0)
    scheduler.start()

    # 앱 종료 시 스케줄러도 종료
    import atexit
    atexit.register(lambda: scheduler.shutdown())
