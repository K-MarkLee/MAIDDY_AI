import jwt
from decouple import config

class TokenManager:
    @staticmethod
    def validate_token(token: str) -> bool:
        """
        JWT 토큰 유효성을 검사합니다.
        """
        try:
            jwt.decode(token, config("JWT_SECRET"), algorithms=["HS256"])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
