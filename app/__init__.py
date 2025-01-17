# app/__init__.py

from flask import Flask
from config import Config
from app.extensions import db, migrate



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # DB 설정
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # DB와 Migrate 초기화
    db.init_app(app)
    migrate.init_app(app, db)

    
    from app.routes.chatbot import chatbot_bp
    from app.routes.feedback import feedback_bp
    from app.routes.recommend import recommend_bp
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
    app.register_blueprint(feedback_bp, url_prefix='/feedback')
    app.register_blueprint(recommend_bp, url_prefix='/recommend')
    
    return app
