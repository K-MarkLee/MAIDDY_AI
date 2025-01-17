from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app.models import User, Summary, UserPattern
from app.extensions import db
from flask import current_app
from app.utils.llm_service import LLMService
import asyncio

llm_service = LLMService()

async def update_patterns():
    # 비동기 함수로 변경
    users = User.query.all()
    for user in users:
        await llm_service.update_user_patterns(user.id)

def schedule_pattern_updates():
    # 스케줄러에서 호출할 동기 함수
    asyncio.run(update_patterns())

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        schedule_pattern_updates,  # 비동기 래퍼 함수 사용
        'interval',
        hours=24
    )
    scheduler.start()
