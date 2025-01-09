from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Django API 기본 URL
DJANGO_API_BASE_URL = "http://web:8000/api/users"


@app.route('/api/users/create/', methods=['POST'])
def create_user():
    """회원가입 API - Django로 요청 전달"""
    user_data = request.json  # 클라이언트에서 받은 데이터
    print("전달된 데이터:", user_data)  # 로그 추가

    # 필수 필드 검증
    required_fields = ["username", "email", "password"]
    if not all(field in user_data for field in required_fields):
        return jsonify({"error": "필수 데이터가 누락되었습니다."}), 400

    django_url = f"{DJANGO_API_BASE_URL}/create/"  # Django 회원가입 API 경로
    try:
        response = requests.post(django_url, json=user_data)  # Django API 호출
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        print("Django 응답 상태 코드:", response.status_code)
        print("Django 응답 내용:", response.text)  # Django에서 반환된 에러 메시지 출력
        return jsonify({"error": "Django API 요청 실패", "details": response.text}), 500



@app.route('/api/users/login/', methods=['POST'])
def login():
    """로그인 API - Django로 요청 전달"""
    login_data = request.json  # 클라이언트에서 받은 데이터

    # 필수 필드 검증
    required_fields = ["email", "password"]
    if not all(field in login_data for field in required_fields):
        return jsonify({"error": "이메일 또는 비밀번호가 누락되었습니다."}), 400

    django_url = f"{DJANGO_API_BASE_URL}/login/"  # Django 로그인 API 경로
    try:
        response = requests.post(django_url, json=login_data)  # Django API 호출
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Django API 요청 실패", "details": str(e)}), 500


@app.route('/token/refresh/', methods=['POST'])
def refresh_token():
    """토큰 갱신 API - Django로 요청 전달"""
    refresh_data = request.json  # 클라이언트에서 받은 데이터

    # 필수 필드 검증
    if "refresh" not in refresh_data:
        return jsonify({"error": "Refresh 토큰이 누락되었습니다."}), 400

    django_url = f"{DJANGO_API_BASE_URL}/token/refresh/"  # Django 토큰 갱신 API 경로
    try:
        response = requests.post(django_url, json=refresh_data)  # Django API 호출
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Django API 요청 실패", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
