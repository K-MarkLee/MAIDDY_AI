# app/models.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
from app import db



class User(db.Model):
    # 사용자 정보를 저장하는 테이블
    __tablename__ = "users_user"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    
    # 관계 설정
    diaries = db.relationship('Diary', backref='user', lazy=True)
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    todo = db.relationship('Todo', backref='user', lazy=True)
    ai_responses = db.relationship('AiResponse', backref='user', lazy=True)
    summaries = db.relationship('Summary', backref='user', lazy=True)
    patterns = db.relationship('UserPattern', backref='user', lazy=True)
    embeddings = db.relationship('Embedding', backref='user', lazy=True)



class Diary(db.Model):
    # 일기 정보를 저장하는 테이블
    __tablename__ = "diaries_diary"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    select_date = db.Column(db.Date, nullable=False)


class Schedule(db.Model):
    # 일정 정보를 저장하는 테이블
    __tablename__ = "schedules_schedule"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    select_date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False) # HH:MM 형식으로 저장


class Todo(db.Model):
    # 할일 정보를 저장하는 테이블
    __tablename__ = "todo_todo"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    select_date = db.Column(db.Date, nullable=False)


class AiResponse(db.Model):
    # AI의 응답을 저장하는 테이블
    __tablename__ = "ai_responses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    select_date = db.Column(db.Date, nullable=False)
    response_type = db.Column(db.String(20), nullable=False)



class Summary(db.Model):
    __tablename__ = "summaries_summary"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    select_date = db.Column(db.Date, nullable=False)


class Embedding(db.Model):
    """텍스트 임베딩을 저장하는 모델"""
    __tablename__ = 'embeddings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    embedding = db.Column(Vector(1536))  # OpenAI의 text-embedding-ada-002 모델은 1536 차원
    metadata = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('embeddings', lazy=True))

    __table_args__ = (
        db.Index('ix_embeddings_embedding', 'embedding', postgresql_using='ivfflat'),
    )
