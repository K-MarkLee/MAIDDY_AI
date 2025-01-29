FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    libomp-dev \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Seoul

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
