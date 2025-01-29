from app.extensions import db
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


class User(db.Model):
    __tablename__ = "users_user"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    diaries = db.relationship('Diary', backref='user', lazy=True)
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    todo = db.relationship('Todo', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    summaries = db.relationship('Summary', backref='user', lazy=True)
    embeddings = db.relationship('Embedding', backref='user', lazy=True)
    cleaned_data = db.relationship('CleanedData', backref='user', lazy=True)


class Diary(db.Model):
    __tablename__ = "diaries_diary"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    select_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Schedule(db.Model):
    __tablename__ = "schedules_schedule"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    select_date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)  # HH:MM:SS 형식으로 저장
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Todo(db.Model):
    __tablename__ = "todo_todo"
    __table_args__ = {'extend_existing': True}  # 기존 테이블 확장

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    select_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id', ondelete='CASCADE'), nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    select_date = db.Column(db.Date, nullable=False)

class CleanedData(db.Model):
    __tablename__ = 'cleaned_data'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id', ondelete='CASCADE'), nullable=False)
    select_date = db.Column(db.Date, nullable=False)
    cleaned_text = db.Column(db.Text, nullable=False)
    

class Summary(db.Model):
    __tablename__ = 'summaries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id', ondelete='CASCADE'), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # monthly, weekly
    start_date = db.Column(db.Date, nullable=False)  # 요약 시작일
    end_date = db.Column(db.Date, nullable=False)    # 요약 종료일
    
    __table_args__ = (
        db.Index('idx_summary_user_type_dates', 'user_id', 'type', 'start_date', 'end_date'),
    )


class Embedding(db.Model):
    """텍스트 임베딩을 저장하는 모델"""
    __tablename__ = 'embeddings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id', ondelete='CASCADE'), nullable=False)
    summary_id = db.Column(db.Integer, db.ForeignKey('summaries.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'weekly' or 'monthly'
    embedding = db.Column(Vector(1536))
    start_date = db.Column(db.Date, nullable=False)  # 임베딩 시작일
    end_date = db.Column(db.Date, nullable=False)    # 임베딩 종료일
    
    __table_args__ = (
        db.Index('idx_embedding_user_type_dates', 'user_id', 'type', 'start_date', 'end_date'),
    )