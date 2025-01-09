from flask import Flask
from app.database import db


app = Flask(__name__)

# DB 설정
app.config['SQLALCHEMY_DATABASE_URI'] = (
    "postgresql://maiddy_admin:youngpotygotop123@db:5432/maiddy_db" # 지워야 공유가능
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB 초기화
db.init_app(app)

# 블루프린트 등록
from app.routes import main
app.register_blueprint(main)
