FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

# gunicorn을 사용하여 Flask 앱 실행
# CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]  # app.py의 app 객체를 gunicorn을 통해 실행
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
