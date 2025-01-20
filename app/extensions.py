"""
Flask 확장 모듈

이 모듈은 Flask 애플리케이션에서 사용되는 확장들을 초기화합니다.
현재 사용 중인 확장:
- SQLAlchemy: 데이터베이스 ORM
- Migrate: 데이터베이스 마이그레이션 관리
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 데이터베이스 ORM 인스턴스
db = SQLAlchemy()

# 데이터베이스 마이그레이션 인스턴스
migrate = Migrate()