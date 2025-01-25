"""
MAIDDY AI 애플리케이션의 라우트 모듈
모든 블루프린트를 여기서 import하여 다른 모듈에서 쉽게 사용할 수 있도록 함
"""

from .chatbot import chatbot_bp
from .feedback import feedback_bp
from .recommend import recommend_bp

__all__ = [
    'chatbot_bp',
    'feedback_bp',
    'recommend_bp'
]
