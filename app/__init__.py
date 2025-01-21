"""
MAIDDY AI 애플리케이션의 메인 초기화 모듈
"""

from flask import Flask, jsonify
from config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    """Flask 애플리케이션 팩토리 함수"""
    app = Flask(__name__)
    
    # 기본 설정 로드
    app.config.from_object(config_class)
    
    # 데이터베이스 설정
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 확장 초기화
    db.init_app(app)
    migrate.init_app(app, db)
    
    # 블루프린트 등록
    register_blueprints(app)
    
    # 스케줄러 초기화
    with app.app_context():
        from app.scheduler import init_scheduler
        
        # 스케줄러 초기화
        success, message = init_scheduler()
        if not success:
            app.logger.error(f"Failed to initialize scheduler: {message}")
        else:
            app.logger.info(message)
    
    return app


def register_blueprints(app):
    """블루프린트 등록"""
    from app.routes.chatbot import chatbot_bp
    from app.routes.feedback import feedback_bp
    from app.routes.recommend import recommend_bp
    
    app.register_blueprint(feedback_bp, url_prefix='/feedback')
    app.register_blueprint(recommend_bp, url_prefix='/recommend')
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
