from flask import Blueprint, request, jsonify
from app.database import db
from app.models import Diary, AIData
from langchain import LLMChain, PromptTemplate
from langchain.llms import OpenAI
from dotenv import load_dotenv
import openai
import jwt
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import json
import os

# .env 파일 로드
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")  # JWT 서명 키
main = Blueprint('main', __name__)

# JWT 디코더
def decode_jwt(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}

# 1. 하루 평가 API
@main.route("/api/evaluate_day", methods=["POST"])
def evaluate_day():
    data = request.json
    user_id = data.get("user_id")
    date = data.get("date")

    if not user_id or not date:
        return jsonify({"error": "user_id와 date가 필요합니다."}), 400

    diary = Diary.query.filter_by(user_id=user_id, date=date).first()
    if not diary:
        return jsonify({"error": "해당 날짜의 일기를 찾을 수 없습니다."}), 404

    todo = data.get("todo", [])

    # LangChain의 PromptTemplate 사용
    template = """
    유저의 하루 평가를 도와주세요.
    - 일기: {diary_content}
    - 할 일 목록: {todo_list}
    """
    prompt = PromptTemplate(
        input_variables=["diary_content", "todo_list"], 
        template=template
    )

    # LangChain LLMChain 사용
    llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)
    chain = LLMChain(llm=llm, prompt=prompt)

    # LangChain으로 결과 생성
    response = chain.run(diary_content=diary.content, todo_list=todo)

    return jsonify({"comment": response}), 200

# 2. 일정,리스트 추가가 및 텍스트 생성 기능 통합 API
@main.route("/api/chatbot_or_generate", methods=["POST"])
def chatbot_or_generate():
    data = request.json
    user_id = data.get("user_id")
    message = data.get("message")
    prompt = data.get("prompt")

    if not (message or prompt):
        return jsonify({"error": "message 또는 prompt 중 하나는 필요합니다."}), 400

    past_entries = []
    if user_id:
        past_data = Diary.query.filter_by(user_id=user_id).all()
        past_entries = [entry.to_dict() for entry in past_data]

    # LangChain PromptTemplate 사용
    if message:
        template = """
        유저와의 대화 내용: "{message}"
        - 과거 데이터: {past_entries}
        - 위 정보를 바탕으로 대화 내용을 생성하고, 필요하면 일정이나 할 일 목록에 추가해야 할지 결정하세요.
        """
        prompt_template = PromptTemplate(
            input_variables=["message", "past_entries"],
            template=template
        )
        llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)
        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.run(message=message, past_entries=past_entries)
        return jsonify({"response": response}), 200

    elif prompt:
        prompt_template = PromptTemplate.from_template("{prompt}")
        llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)
        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.run(prompt=prompt)
        return jsonify({"generated_text": response}), 200

# 3. 유저 루틴 설정 API
@main.route("/api/recommend_routine", methods=["GET"])
def recommend_routine():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id가 필요합니다."}), 400

    past_data = Diary.query.filter_by(user_id=user_id).all()
    if not past_data:
        return jsonify({"error": "과거 데이터를 찾을 수 없습니다."}), 404

    past_entries = [entry.to_dict() for entry in past_data]

    # LangChain PromptTemplate 사용
    template = """
    다음은 유저의 과거 일기 및 데이터입니다: {past_entries}
    이 데이터를 바탕으로 유저의 일상 루틴을 추천해주세요.
    """
    prompt = PromptTemplate(
        input_variables=["past_entries"],
        template=template
    )

    llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)
    chain = LLMChain(llm=llm, prompt=prompt)

    response = chain.run(past_entries=past_entries)

    return jsonify({"routine": response}), 200

# 4. 키워드 추출 API
@main.route("/api/keywords/extract", methods=["POST"])
def extract_keywords():
    data = request.json
    text = data.get("text")

    if not text:
        return jsonify({"error": "텍스트가 누락되었습니다."}), 400

    # LangChain PromptTemplate 사용
    template = "다음 텍스트에서 중요한 키워드를 추출하세요: {text}"
    prompt = PromptTemplate(
        input_variables=["text"],
        template=template
    )

    llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)
    chain = LLMChain(llm=llm, prompt=prompt)

    response = chain.run(text=text)

    return jsonify({"keywords": response}), 200

# 5. 키워드 학습 및 삭제 스케줄러 API
scheduler = BackgroundScheduler()

def scheduled_training_and_deletion():
    with main.app_context():
        training_data = AIData.query.all()
        if training_data:
            # 학습 데이터 준비
            formatted_data = [
                {
                    "prompt": f"데이터: {entry.keywords or entry.todo or entry.diary or entry.schedule}",
                    "completion": "응답 생성"
                }
                for entry in training_data
            ]
            with open("scheduled_training_data.json", "w") as f:
                json.dump(formatted_data, f)

            # OpenAI Fine-Tuning 호출
            openai.api_key = os.getenv("OPENAI_API_KEY")
            try:
                openai.FineTune.create(training_file="scheduled_training_data.json", model="curie")
            except Exception as e:
                print(f"Fine-Tuning 에러: {e}")

            # 데이터 삭제
            db.session.query(AIData).delete()
            db.session.commit()

scheduler.add_job(func=scheduled_training_and_deletion, trigger="interval", days=1)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())