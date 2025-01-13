FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Flask 실행
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
# CMD ["python", "app.py"]

# 마이그레이션 및 Flask 애플리케이션 실행
# CMD ["flask", "db", "upgrade"] && ["python", "app.py"]
CMD sh -c "flask db upgrade && python app.py"