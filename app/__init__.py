"""
Flask 인스턴스 생성
DB 초기화
블루 프린트 등록 등을 처리
"""

from flask import Flask
from .database import db
from .models import AiResponse, Diary, Schedule, Todo, User
from .routes.chatbot import chatbot_bp
from .routes.feedback import feedback_bp
from .routes.recommend import recommend_bp
from decouple import config # 환경변수 불러오기
from .scheduler import start_scheduler
from flask_migrate import Migrate


def create_app():
    app = Flask(__name__)
    # 필요하다면 config 설정
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{config('DB_USER')}:{config('DB_PASSWORD')}@{config('DB_HOST')}:{config('DB_PORT')}/{config('DB_NAME')}"
    app.config["JWT_SECRET_KEY"] = config("JWT_SECRET_KEY")
    
    # DB 초기화
    db.init_db(app)

    # 마이그레이션 초기화
    migrate = Migrate(app, db)

    with app.app_context():
        db.create_all()

    # Blueprint 등록
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(feedback_bp, url_prefix="/feedback")
    app.register_blueprint(recommend_bp, url_prefix="/recommend")

    # 스케줄러 시작
    start_scheduler(app)

    return app
