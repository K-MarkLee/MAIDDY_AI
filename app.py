from flask import Flask, request, jsonify
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
import datetime
import openai

# 데이터베이스 설정
DATABASE_URL = "postgresql://maiddy_admin:youngpotygotop123@db:5432/maiddy_db"  # Docker/DBeaver 연결 시 교체 필요
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

# 기존 테이블 참조
Diary = metadata.tables.get('diary')
Checklist = metadata.tables.get('checklist')

# OpenAI API 키 설정
openai.api_key = "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"

# Flask 앱 설정
app = Flask(__name__)

# CORS 설정 (프론트와 연동시 필요)
# from flask_cors import CORS
# CORS(app)

# 기능 1: 일일 평가
@app.route('/evaluate', methods=['GET'])
def evaluate_day():
    user_id = request.args.get('user_id')
    today = datetime.date.today()

    # 일기와 체크리스트 가져오기
    diary_entry = session.execute(Diary.select().where(Diary.c.user_id == user_id, Diary.c.date == today)).fetchone()
    checklist_entries = session.execute(Checklist.select().where(Checklist.c.user_id == user_id, Checklist.c.date == today)).fetchall()

    if not diary_entry and not checklist_entries:
        return jsonify({"message": "오늘 작성된 데이터가 없습니다."})

    comments = []
    if diary_entry:
        comments.append(f"일기 내용: {diary_entry.content}")

    completed_tasks = [task.task for task in checklist_entries if task.status == 'completed']
    if completed_tasks:
        comments.append(f"완료된 작업: {', '.join(completed_tasks)}")
    else:
        comments.append("오늘 완료된 작업이 없습니다.")

    # OpenAI API 호출로 평가 코멘트 생성
    openai_response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"오늘의 일기: {diary_entry.content if diary_entry else '없음'}\n완료된 작업: {', '.join(completed_tasks) if completed_tasks else '없음'}\n이 정보를 바탕으로 하루 평가 코멘트를 작성해 주세요.",
        max_tokens=100
    )

    ai_comment = openai_response['choices'][0]['text'].strip()
    comments.append(f"AI 평가 코멘트: {ai_comment}")

    return jsonify({"evaluation": " \n".join(comments)})

# 기능 2: 챗봇 데이터 추가 및 대화
@app.route('/chat', methods=['POST'])
def chat_with_user():
    data = request.json
    user_input = data.get('message')

    # OpenAI API 호출로 대화 생성
    openai_response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"User: {user_input}\nAI:",
        max_tokens=150,
        temperature=0.7
    )

    ai_response = openai_response['choices'][0]['text'].strip()

    return jsonify({"response": ai_response})

@app.route('/add', methods=['POST'])
def add_entry():
    data = request.json
    user_id = data.get('user_id')
    entry_type = data.get('type')  # 'diary' 또는 'checklist'

    if entry_type == 'diary':
        session.execute(Diary.insert().values(user_id=user_id, date=datetime.date.today(), content=data.get('content')))
    elif entry_type == 'checklist':
        session.execute(Checklist.insert().values(user_id=user_id, date=datetime.date.today(), task=data.get('task'), status='pending'))
    else:
        return jsonify({"error": "잘못된 입력 유형입니다."}), 400

    session.commit()
    return jsonify({"message": f"{entry_type.capitalize()} 항목이 성공적으로 추가되었습니다!"})

# 기능 3: 루틴 추천
@app.route('/routine', methods=['GET'])
def generate_routine():
    user_id = request.args.get('user_id')

    # 과거 데이터 가져오기
    checklist_entries = session.execute(Checklist.select().where(Checklist.c.user_id == user_id)).fetchall()
    task_frequency = {}

    for entry in checklist_entries:
        task_frequency[entry.task] = task_frequency.get(entry.task, 0) + 1

    # 작업 빈도를 기준으로 추천
    sorted_tasks = sorted(task_frequency.items(), key=lambda x: x[1], reverse=True)
    recommended_tasks = [task[0] for task in sorted_tasks[:5]]  # 상위 5개 작업

    return jsonify({"recommended_routine": recommended_tasks})

if __name__ == '__main__':
    app.run(debug=True)
