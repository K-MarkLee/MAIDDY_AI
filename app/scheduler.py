"""
스케줄러 모듈
"""

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from app.models import User, CleanedData, Summary
from app.utils.llm_service import LLMService
from app.utils.embedding import EmbeddingService
import atexit

scheduler = BackgroundScheduler(
    job_defaults={
        'max_instances': 1,
        'misfire_grace_time': 3600,  # 1시간의 유예 시간
        'coalesce': True  # 중복 실행 방지
    },
    timezone=current_app.config.get('TIMEZONE', 'Asia/Seoul')
)

def process_yesterday_data():
    """어제의 데이터 처리 작업"""
    with current_app.app_context():
        yesterday = datetime.now().date() - timedelta(days=1)
        current_app.logger.info(f"Starting daily data processing for {yesterday}")
        
        try:
            llm_service = LLMService()
            
            # 모든 사용자의 데이터 처리
            users = User.query.all()1
            if not users:
                current_app.logger.warning("No users found in the system")
                return
                
            for user in users:
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        # 이미 처리된 데이터가 있는지 확인
                        existing_data = CleanedData.query.filter_by(
                            user_id=user.id,
                            select_date=yesterday
                        ).first()
                        
                        if existing_data:
                            current_app.logger.info(f"Data already exists for user {user.id} on {yesterday}, skipping...")
                            break
                        
                        success, message = llm_service.clean_daily_data(user.id, yesterday)
                        if not success:
                            if "데이터가 없습니다" in message:
                                current_app.logger.info(f"No data found for user {user.id} on {yesterday}, skipping...")
                                break
                            current_app.logger.error(f"Failed to process data for user {user.id}: {message}")
                            retry_count += 1
                        else:
                            current_app.logger.info(f"Successfully processed data for user {user.id}")
                            break
                            
                        if retry_count == max_retries:
                            current_app.logger.error(f"Max retries reached for user {user.id}")
                    except Exception as e:
                        current_app.logger.error(f"Error processing data for user {user.id}: {str(e)}")
                        retry_count += 1
                        if retry_count == max_retries:
                            current_app.logger.error(f"Max retries reached for user {user.id}")
                            break
                    
        except Exception as e:
            current_app.logger.error(f"System-wide error in daily processing: {str(e)}")
        
        current_app.logger.info("Daily data processing completed")

def process_weekly_data():
    """주간 데이터 처리 작업"""
    with current_app.app_context():
        today = datetime.now().date()
        current_app.logger.info(f"Starting weekly data processing for week of {today}")
        
        try:
            embedding_service = EmbeddingService()
            
            # 모든 사용자의 주간 데이터 처리
            users = User.query.all()
            if not users:
                current_app.logger.warning("No users found in the system")
                return
                
            for user in users:
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        # 해당 주의 시작일과 종료일 계산
                        start_date, end_date = embedding_service.get_week_dates(today)
                        
                        # 이미 처리된 주간 요약이 있는지 확인
                        existing_summary = Summary.query.filter(
                            Summary.user_id == user.id,
                            Summary.type == 'weekly',
                            Summary.start_date == start_date,
                            Summary.end_date == end_date
                        ).first()
                        
                        if existing_summary:
                            current_app.logger.info(f"Weekly summary already exists for user {user.id} for week {start_date} to {end_date}, skipping...")
                            break
                        
                        # 해당 주의 CleanedData가 하나라도 있는지 확인
                        has_data = CleanedData.query.filter(
                            CleanedData.user_id == user.id,
                            CleanedData.select_date >= start_date,
                            CleanedData.select_date <= end_date
                        ).first() is not None
                        
                        if not has_data:
                            current_app.logger.info(f"No data found for user {user.id} for week {start_date} to {end_date}, skipping...")
                            break
                        
                        success, message = embedding_service.process_weekly_data(user.id, today)
                        if not success:
                            if "데이터가 없습니다" in message:
                                current_app.logger.info(f"Insufficient data for user {user.id} for week processing, skipping...")
                                break
                            current_app.logger.error(f"Failed to process weekly data for user {user.id}: {message}")
                            retry_count += 1
                        else:
                            current_app.logger.info(f"Successfully processed weekly data for user {user.id}")
                            break
                            
                        if retry_count == max_retries:
                            current_app.logger.error(f"Max retries reached for user {user.id}")
                    except Exception as e:
                        current_app.logger.error(f"Error processing weekly data for user {user.id}: {str(e)}")
                        retry_count += 1
                        if retry_count == max_retries:
                            current_app.logger.error(f"Max retries reached for user {user.id}")
                            break
                    
        except Exception as e:
            current_app.logger.error(f"System-wide error in weekly processing: {str(e)}")
        
        current_app.logger.info("Weekly data processing completed")

def init_scheduler():
    """스케줄러 초기화"""
    try:
        # 매일 00:01에 어제 데이터 처리
        scheduler.add_job(
            func=process_yesterday_data,
            trigger=CronTrigger(hour=0, minute=1),
            id='process_yesterday_data',
            name='Process yesterday data',
            replace_existing=True
        )
        
        # 매주 월요일 00:30에 주간 데이터 처리
        scheduler.add_job(
            func=process_weekly_data,
            trigger=CronTrigger(day_of_week='mon', hour=0, minute=30),
            id='process_weekly_data',
            name='Process weekly data',
            replace_existing=True
        )
        
        scheduler.start()
        
        # 앱 종료 시 스케줄러도 종료
        atexit.register(lambda: scheduler.shutdown(wait=False))
        
        return True, "스케줄러가 성공적으로 초기화되었습니다."
        
    except Exception as e:
        return False, f"스케줄러 초기화 중 오류 발생: {str(e)}"