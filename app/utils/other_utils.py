# app/utils/tokenmanager.py

import requests
import time
from decouple import config
from flask import current_app
from app.models import User
from app.database import db

class TokenManager:
    def __init__(self):
        self.base_url = config("TOKEN_BASE_URL")  # .env에 설정된 기본 URL
        self.access_token = None
        self.refresh_token = None
        self.access_token_expires = 0

    def set_token(self, access_token: str, refresh_token: str, expires_in_sec: int):
        """
        Access token과 Refresh token을 설정하고 만료 시간을 계산합니다.
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.access_token_expires = int(time.time()) + expires_in_sec
        current_app.logger.info("Tokens have been set successfully.")

    def valid_token(self) -> bool:
        """
        현재 Access token이 유효한지 확인합니다.
        """
        return time.time() < self.access_token_expires

    def refresh_access_token(self):
        """
        Refresh token을 사용하여 Access token을 갱신합니다.
        """
        if not self.refresh_token:
            current_app.logger.error("Refresh 토큰이 없습니다.")
            raise Exception("Refresh 토큰이 없습니다.")
        
        url = f"{self.base_url}/api/users/token/refresh/"
        data = {"refresh": self.refresh_token}
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            json_data = response.json()
            new_access = json_data.get("access")
            new_refresh = json_data.get("refresh", self.refresh_token)

            expires_in = json_data.get("expires_in", 1800)  # 기본 만료 시간 30분

            self.set_token(new_access, new_refresh, expires_in)
            current_app.logger.info("Access token이 성공적으로 갱신되었습니다.")
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"토큰 갱신 실패: {e}")
            raise Exception("토큰 갱신 실패")

    def get_valid_access_token(self) -> str:
        """
        유효한 Access token을 반환합니다. 만료된 경우 갱신을 시도합니다.
        """
        if not self.valid_token():
            current_app.logger.info("Access token이 만료되었습니다. 갱신을 시도합니다.")
            self.refresh_access_token()
        return self.access_token

    def associate_tokens_with_user(self, user_id: str, access_token: str, refresh_token: str, expires_in_sec: int):
        """
        특정 사용자와 토큰을 연동합니다.
        :param user_id: 사용자 ID
        :param access_token: Access token
        :param refresh_token: Refresh token
        :param expires_in_sec: Access token의 만료 시간(초 단위)
        """
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            current_app.logger.error(f"사용자 {user_id}를 찾을 수 없습니다.")
            raise Exception("사용자를 찾을 수 없습니다.")
        
        user.access_token = access_token
        user.refresh_token = refresh_token
        user.access_token_expires = int(time.time()) + expires_in_sec
        db.session.commit()
        current_app.logger.info(f"사용자 {user_id}의 토큰이 성공적으로 업데이트되었습니다.")

    def load_tokens_from_user(self, user_id: str):
        """
        특정 사용자로부터 토큰을 로드합니다.
        :param user_id: 사용자 ID
        """
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            current_app.logger.error(f"사용자 {user.user_name}를 찾을 수 없습니다.")
            raise Exception("사용자를 찾을 수 없습니다.")
        
        self.access_token = user.access_token
        self.refresh_token = user.refresh_token
        self.access_token_expires = user.access_token_expires
        current_app.logger.info(f"사용자 {user.user_name}의 토큰이 로드되었습니다.")
