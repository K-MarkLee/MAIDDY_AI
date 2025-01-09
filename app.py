from flask import Flask
from app.database import db
from app.routes import main  # routes.py의 Blueprint 가져오기
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 데이터베이스 초기화
db.init_app(app)

# Blueprint 등록
app.register_blueprint(main)

# 애플리케이션 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
