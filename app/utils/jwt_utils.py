import jwt
from flask import request, jsonify
from functools import wraps
from decouple import config
from flask import current_app

# 환경 변수에서 JWT 비밀 키 가져오기
JWT_SECRET = config("JWT_SECRET")
JWT_ALGORITHM = config("JWT_ALGORITHM")

# def decode_jwt(token: str):
#     """JWT 토큰 디코딩. 문제 있으면 예외 발생."""
#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithms=JWT_ALGORITHM)
#         return payload
#     except jwt.ExpiredSignatureError:
#         return {"error": "토큰이 만료되었습니다."}
#     except jwt.InvalidTokenError:
#         return {"error": "유효하지 않은 토큰입니다."}
#     return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

# def get_jwt_payload():
#     """
#     요청 헤더에서 Authorization 필드의 토큰을 추출하고 디코딩하여 payload 리턴.
#     """
#     auth_header = request.headers.get("Authorization", "")
#     if not auth_header.startswith("Bearer "):
#         return None
#     token = auth_header.split(" ")[1]
#     try:
#         return decode_jwt(token)
#     except jwt.exceptions.InvalidTokenError:
#         return None

# def require_jwt(fn):
#     """
#     JWT 토큰 검증 데코레이터: 토큰이 유효하면 사용자 객체를 함수에 전달.
#     """
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         payload = get_jwt_payload()
#         if payload is None:
#             return jsonify({"error": "유효하지 않는 토큰입니다."}), 401
#         user_id = payload.get('sub')  # JWT에서 사용자 ID 가져오기
#         if not user_id:
#             return jsonify({"error": "토큰에 사용자 ID가 없습니다."}), 401
#         user = User.query.filter_by(id=user_id).first()
#         if not user:
#             return jsonify({"error": "사용자를 찾을 수 없습니다."}), 401
#         return fn(user, *args, **kwargs)
#     return wrapper



def require_jwt(fn):
    """
    JWT가 유효한 경우 user_id를 함수에 전달
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            current_app.logger.error(f"Authorization 헤더가 잘못되었습니다: {auth_header}")
            return jsonify({"error": "유효하지 않는 토큰입니다."}), 401

        token = auth_header.split(" ")[1]
        current_app.logger.info(f"받은 토큰: {token}")  # 디버깅을 위해 토큰 출력

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_app.logger.info(f"디코딩된 페이로드: {payload}")  # 디버깅을 위해 페이로드 출력
        except jwt.ExpiredSignatureError:
            current_app.logger.error("토큰의 유효기간이 만료되었습니다.")
            return jsonify({"error": "토큰의 유효기간이 만료되었습니다."}), 401
        except jwt.InvalidTokenError as e:
            current_app.logger.error(f"유효하지 않은 토큰입니다: {e}")
            return jsonify({"error": "유효하지 않는 토큰입니다."}), 401

        # `user_id` 추출
        user_id = payload.get("user_id")
        if not user_id:
            current_app.logger.error("페이로드에 user_id가 포함되어 있지 않습니다.")
            return jsonify({"error": "유효하지 않는 토큰입니다."}), 401

        return fn(user_id, *args, **kwargs)  # user_id를 함수에 전달
    return wrapper
