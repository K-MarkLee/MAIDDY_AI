# app/utils/jwt_utils.py

import jwt
from flask import request, jsonify, current_app
from functools import wraps
from decouple import config
from app.models import User
from app.database import db

# 환경 변수에서 JWT 비밀 키 가져오기
JWT_SECRET = config("JWT_SECRET", "secret")  # .env에서 가져옴
JWT_ALGORITHM = "HS256"

def decode_jwt(token: str):
    """JWT 토큰 디코딩. 문제있으면 예외 발생."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def get_jwt_payload():
    """
    Authorization: Bearer <TOKEN> 헤더에서
    토큰을 추출하고 디코딩 후 payload 리턴.
    없거나 잘못됐으면 None
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = decode_jwt(token)
        return payload
    except jwt.exceptions.InvalidTokenError:
        return None

def require_jwt(fn):
    """
    데코레이터: JWT가 유효하면 사용자 객체를 함수에 전달, 아니면 401 리턴
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = get_jwt_payload()
        if payload is None:
            return jsonify({"error": "유효하지 않는 토큰입니다."}), 401
        user_id = payload.get('sub')
        if not user_id:
            return jsonify({"error": "유효하지 않는 토큰입니다."}), 401
        # 데이터베이스에서 사용자 조회
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({"error": "사용자를 찾을 수 없습니다."}), 401
        # 함수에 사용자 객체 전달
        return fn(user, *args, **kwargs)
    return wrapper
