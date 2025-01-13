"""
ORM 모델
"""


from .database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import VECTOR


class User(db.Model):
    # 사용자 정보를 저장하는 테이블
    __tablename__ = "users_user"

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(255), nullable=False, unique=True)

    # 관계 설정
    diaries = db.relationship('Diary', backref='user', lazy=True)
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    todo = db.relationship('Todo', backref='user', lazy=True)
    ai_responses = db.relationship('AiResponse', backref='user', lazy=True)
    summaries = db.relationship('Summary', backref='user', lazy=True)



class AiResponse(db.Model):
    # AI의 응답을 저장하는 테이블
    __tablename__ = "ai_responses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users_user.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    select_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())  #now는 현재 시간을 가져오는 함수   
    embedding = db.Column(VECTOR)
    


class Diary(db.Model):
    # 일기 정보를 저장하는 테이블
    __tablename__ = "diaries_diary"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users_user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    select_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())


class Schedule(db.Model):
    # 일정 정보를 저장하는 테이블
    __tablename__ = "schedules_schedule"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users_user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    select_date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())


class Todo(db.Model):
    # 할일 정보를 저장하는 테이블
    __tablename__ = "todo_todo"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users_user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    select_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())



class Summary(db.Model):
    __tablename__ = "summaries_summary"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users_user.id'), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    embedding = db.Column(VECTOR(1536)) 
    select_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())