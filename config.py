from decouple import config

class Config:
    # Database
    DB_NAME = config('DB_NAME', default='maiddy_db')
    DB_USER = config('DB_USER', default='maiddy_admin')
    DB_PASSWORD = config('DB_PASSWORD')
    DB_HOST = config('DB_HOST', default='db')
    DB_PORT = config('DB_PORT', default='5432')
    
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = config('SQLALCHEMY_TRACK_MODIFICATIONS', default=False, cast=bool)
    
    # OpenAI
    OPENAI_API_KEY = config('OPENAI_API_KEY')
    OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o-mini')
    OPENAI_TEMPERATURE = config('OPENAI_TEMPERATURE', default=0.7, cast=float)
 
    # Timezone
    TIMEZONE = config('TIMEZONE', default='Asia/Seoul')
