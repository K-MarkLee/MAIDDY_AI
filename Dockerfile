FROM python:3.9-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Flask 실행
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
# CMD ["python", "app.py"]

# 마이그레이션 및 Flask 애플리케이션 실행
# CMD ["flask", "db", "upgrade"] && ["python", "app.py"]
CMD ["python", "app.py"]