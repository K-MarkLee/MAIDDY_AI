"""
JWT 토큰을 파싱/검증
"""

import jwt
from flask import request, jsonify
from functools import wraps
from decouple import config


JWT_SECRET = config("JWT_SECRET", "secret")  # .env에서 가져옴
JWT_ALGORITHM = "HS256"


def decode_jwt(token: str):
    """JWT 토큰 디코딩. 문제있으면 예외 발생."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_jwt_payload():
    """
    Authorization: Bearer <TOKEN> 헤더에서
    token을 추출하고 디코딩 후 payload 리턴.
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
    데코레이터: JWT가 유효하면 함수 실행, 아니면 401 리턴
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = get_jwt_payload()
        if payload is None:
            return jsonify({"error": "유효하지 않는 토큰입니다."}), 401
        return fn(payload, *args, **kwargs)
    return wrapper
