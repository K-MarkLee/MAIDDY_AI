from flask import Flask, jsonify
from config import Config
from app.extensions import db, migrate
from app.routes.chatbot import chatbot_bp
from app.routes.feedback import feedback_bp
from app.routes.recommend import recommend_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    
    app.config.from_object(config_class)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    register_blueprints(app)
    
    with app.app_context():
        from app.scheduler import init_scheduler, init_app
        
        init_app(app)
        
        success, message = init_scheduler()
        if not success:
            app.logger.error(f"Failed to initialize scheduler: {message}")
        else:
            app.logger.info(message)
    
    return app


def register_blueprints(app):
    app.register_blueprint(feedback_bp, url_prefix='/feedback')
    app.register_blueprint(recommend_bp, url_prefix='/recommend')
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
