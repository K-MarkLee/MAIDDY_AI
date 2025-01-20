from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.models import User, CleanedData
from app.utils.llm_service import LLMService
from app.extensions import db
from flask import current_app
import atexit

scheduler = BackgroundScheduler()
MAX_RETRIES = 3  # 최대 재시도 횟수

def process_yesterday_data():
    """어제 데이터 전처리 작업"""
    with current_app.app_context():
        yesterday = datetime.now().date() - timedelta(days=1)
        current_app.logger.info(f"Starting daily data processing for {yesterday}")
        
        # 모든 사용자 조회
        users = User.query.all()
        llm_service = LLMService()
        
        for user in users:
            retries = 0
            while retries < MAX_RETRIES:
                try:
                    # 이미 처리된 데이터가 있는지 확인
                    existing_data = CleanedData.query.filter_by(
                        user_id=user.id,
                        select_date=yesterday
                    ).first()
                    
                    if existing_data:
                        current_app.logger.info(f"Data already processed for user {user.id} on {yesterday}")
                        break
                    
                    # 데이터 전처리 시도
                    success, cleaned_text = llm_service.clean_daily_data(user.id, yesterday)
                    
                    if success:
                        current_app.logger.info(f"Successfully processed data for user {user.id} on {yesterday}")
                        break
                    else:
                        current_app.logger.info(f"No data to process for user {user.id} on {yesterday}")
                        break
                        
                except Exception as e:
                    retries += 1
                    if retries >= MAX_RETRIES:
                        current_app.logger.error(f"Failed to process data for user {user.id} after {MAX_RETRIES} attempts: {str(e)}")
                    else:
                        current_app.logger.warning(f"Retry {retries}/{MAX_RETRIES} for user {user.id}: {str(e)}")
                        continue
        
        current_app.logger.info("Daily data processing completed")

def init_scheduler():
    """스케줄러 초기화"""
    try:
        if scheduler.running:
            scheduler.shutdown()
        
        # 매일 00:01에 실행
        scheduler.add_job(
            process_yesterday_data,
            trigger=CronTrigger(hour=0, minute=1),
            id='daily_data_processor',
            replace_existing=True
        )
        
        scheduler.start()
        
        # 앱 종료 시 스케줄러도 종료
        atexit.register(lambda: scheduler.shutdown(wait=False))
        
        return True, "Scheduler initialized successfully"
        
    except Exception as e:
        return False, f"Failed to initialize scheduler: {str(e)}"

def test_scheduler():
    """스케줄러 테스트"""
    try:
        if not scheduler.running:
            return False, "Scheduler is not running"
        
        jobs = scheduler.get_jobs()
        if not jobs:
            return False, "No jobs scheduled"
        
        daily_job = scheduler.get_job('daily_data_processor')
        if not daily_job:
            return False, "Daily data processor job not found"
        
        next_run = daily_job.next_run_time
        return True, f"Next scheduled run: {next_run}"
        
    except Exception as e:
        return False, f"Scheduler test failed: {str(e)}"