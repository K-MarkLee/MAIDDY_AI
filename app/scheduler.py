from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from app.models import User, CleanedData, Summary
from app.utils.llm_service import LLMService
from app.utils.embedding import EmbeddingService
import atexit

flask_app = None

def init_app(app):
    """Flask 앱 초기화"""
    global flask_app
    flask_app = app

scheduler = BackgroundScheduler(
    job_defaults={
        'max_instances': 1,
        'misfire_grace_time': 3600,  # 1시간의 유예 시간
        'coalesce': True  # 중복 실행 방지
    }
)

def process_yesterday_data():
    if not flask_app:
        raise RuntimeError("Flask 앱이 초기화되지 않았습니다")
        
    with flask_app.app_context():
        try:
            llm_service = LLMService()
            
            users = User.query.with_entities(User.id, User.username).all()
            if not users:
                flask_app.logger.warning("시스템에 사용자가 없습니다")
                return
                
            for user in users:
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        yesterday = datetime.now().date() - timedelta(days=1)
                        
                        existing_data = CleanedData.query.filter(
                            CleanedData.user_id == user.id,
                            CleanedData.select_date == yesterday
                        ).first()
                        
                        if existing_data:
                            flask_app.logger.info(f"사용자 {user.id}의 {yesterday} 데이터가 이미 처리되었습니다, 건너뜁니다...")
                            break
                        
                        success, message = llm_service.clean_daily_data(user.id, yesterday)
                        
                        if success:
                            flask_app.logger.info(f"사용자 {user.id}의 {yesterday} 데이터가 성공적으로 처리되었습니다")
                            
                            success, message = llm_service.create_feedback(user.id, yesterday)
                            if success:
                                flask_app.logger.info(f"사용자 {user.id}의 {yesterday} 피드백이 성공적으로 생성되었습니다")
                            else:
                                flask_app.logger.error(f"사용자 {user.id}의 피드백 생성 실패: {message}")
                            break
                        else:
                            retry_count += 1
                            if retry_count == max_retries:
                                flask_app.logger.error(f"사용자 {user.id}의 데이터 처리 최대 재시도 횟수 초과: {message}")
                            else:
                                flask_app.logger.warning(f"사용자 {user.id}의 데이터 처리 재시도 중 ({retry_count}/{max_retries}): {message}")
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            flask_app.logger.error(f"사용자 {user.id}의 데이터 처리 중 오류 발생: {str(e)}")
                        else:
                            flask_app.logger.warning(f"사용자 {user.id}의 데이터 처리 재시도 중 ({retry_count}/{max_retries})")
                            
        except Exception as e:
            flask_app.logger.error(f"일일 데이터 처리 중 오류 발생: {str(e)}")
            return
            
        flask_app.logger.info("일일 데이터 처리가 완료되었습니다")

def process_weekly_data():
    if not flask_app:
        raise RuntimeError("Flask 앱이 초기화되지 않았습니다")
        
    with flask_app.app_context():
        today = datetime.now().date()
        
        try:
            embedding_service = EmbeddingService()
            
            users = User.query.with_entities(User.id, User.username).all()
            if not users:
                flask_app.logger.warning("시스템에 사용자가 없습니다")
                return
                
            for user in users:
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        start_date, end_date = embedding_service.get_week_dates(today)
                        
                        existing_summary = Summary.query.filter(
                            Summary.user_id == user.id,
                            Summary.type == 'weekly',
                            Summary.start_date == start_date,
                            Summary.end_date == end_date
                        ).first()
                        
                        if existing_summary:
                            flask_app.logger.info(f"사용자 {user.id}의 {start_date}~{end_date} 주간 요약이 이미 존재합니다, 건너뜁니다...")
                            break
                        
                        has_data = CleanedData.query.filter(
                            CleanedData.user_id == user.id,
                            CleanedData.select_date >= start_date,
                            CleanedData.select_date <= end_date
                        ).first()
                        
                        if not has_data:
                            flask_app.logger.info(f"사용자 {user.id}의 {start_date}~{end_date} 기간 동안의 데이터가 없습니다, 건너뜁니다...")
                            break
                            
                        success, message = embedding_service.process_weekly_data(user.id, today)
                        
                        if success:
                            flask_app.logger.info(f"사용자 {user.id}의 주간 데이터가 성공적으로 처리되었습니다")
                            break
                        else:
                            retry_count += 1
                            if retry_count == max_retries:
                                flask_app.logger.error(f"사용자 {user.id}의 주간 데이터 처리 최대 재시도 횟수 초과: {message}")
                            else:
                                flask_app.logger.warning(f"사용자 {user.id}의 주간 데이터 처리 재시도 중 ({retry_count}/{max_retries}): {message}")
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            flask_app.logger.error(f"사용자 {user.id}의 주간 데이터 처리 중 오류 발생: {str(e)}")
                        else:
                            flask_app.logger.warning(f"사용자 {user.id}의 주간 데이터 처리 재시도 중 ({retry_count}/{max_retries})")
                            
        except Exception as e:
            flask_app.logger.error(f"주간 데이터 처리 중 오류 발생: {str(e)}")
            return
            
        flask_app.logger.info("주간 데이터 처리가 완료되었습니다")

def init_scheduler():
    try:
        scheduler.add_job(
            process_yesterday_data,
            'cron',
            hour=0,
            minute=1,
            id='process_yesterday_data'
        )
        
        scheduler.add_job(
            process_weekly_data,
            'cron',
            day_of_week='mon',
            hour=1,
            minute=0,
            id='process_weekly_data'
        )
        
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
        
        return True, "스케줄러가 성공적으로 초기화되었습니다"
    except Exception as e:
        return False, f"스케줄러 초기화 중 오류 발생: {str(e)}"