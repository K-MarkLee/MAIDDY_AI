import requests
import time
import os
from decouple import config

class TokenManager:
    def __init__(self, base_url:str):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.access_token_expires = 0

    
    def set_token(self, access_token:str, refresh_token:str, expires_in_sec:int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.access_token_expires = int(time.time()) + expires_in_sec


    def valid_token(self) -> bool:
        return time.time() < self.access_token_expires
    


    def refresh_access_token(self):
        if not self.refresh_token:
            raise Exception("Refresh 토큰이 없습니다.")
        
        url = f"{self.base_url}/api/users/token/refresh/"
        data = {"refresh": self.refresh_token}
        response = requests.post(url, json=data)

        if response.status_code == 200:
            json_data = response.json()
            new_access = json_data["access"]
            new_refresh = json_data.get("refresh", self.refresh_token)

            expires_in = 1800

            self.set_token(new_access, new_refresh, expires_in)
        else:
            raise Exception("토큰 갱신 실패")
        
    
    def get_valid_access_token(self) -> str:
        if not self.valid_token():
            self.refresh_access_token()
        return self.access_token