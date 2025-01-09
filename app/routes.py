from flask import Blueprint, request, jsonify
from app.database import db
from app.models import Diary
import jwt

SECRET_KEY = "your_secret_key"  # JWT 토큰 서명 키 (환경 변수로 설정 추천)

main = Blueprint('main', __name__)

def decode_jwt(token):
    """
    JWT 토큰을 디코딩하여 사용자 정보를 추출합니다.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}

@main.route("/api/diaries/detail/", methods=["GET"])
def get_diary():
    """
    JWT 토큰에서 user_id를 추출하고, 특정 날짜의 일기 데이터를 조회합니다.
    """
    # Authorization 헤더에서 JWT 토큰 추출
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization header is missing or invalid"}), 401

    token = auth_header.split(" ")[1]
    decoded_token = decode_jwt(token)

    if "error" in decoded_token:
        return jsonify({"error": decoded_token["error"]}), 401

    # JWT 토큰에서 user_id 가져오기
    user_id = decoded_token.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID not found in token"}), 401

    # 쿼리 매개변수에서 날짜 가져오기
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "'date' query parameter is required"}), 400

    # DB에서 일기 데이터 조회
    diary = Diary.query.filter_by(user_id=user_id, date=date).first()
    if not diary:
        return jsonify({"error": "Diary not found"}), 404

    return jsonify(diary.to_dict()), 200
