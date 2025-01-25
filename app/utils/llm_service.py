from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from app.models import Todo, Diary, Schedule, CleanedData, Feedback, Summary, Embedding
from app.extensions import db
from flask import current_app
from app.utils.embedding import EmbeddingService

class LLMService:
    def __init__(self):
        self.chat_model = None
        self.embedding_service = None
        
    def _init_model(self):
        """모델 초기화"""
        if not self.chat_model:
            self.chat_model = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                temperature=current_app.config['OPENAI_TEMPERATURE'],
                api_key=current_app.config['OPENAI_API_KEY']
            )
           
    def _init_embedding_service(self):
        """임베딩 서비스 초기화"""
        if not self.embedding_service:
            self.embedding_service = EmbeddingService()

    def _get_similar_summaries(self, user_id: int, query: str, limit: int = 3) -> List[str]:
        """유사한 주간 요약 검색"""
        self._init_embedding_service()
        self.embedding_service._init_model()  # 임베딩 모델 초기화 추가
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedding_service._create_embedding(query)
            
            # Vector 검색
            similar_summaries = Embedding.query.filter_by(
                user_id=user_id,
                type='weekly'
            ).order_by(
                Embedding.embedding.cosine_distance(query_embedding)
            ).limit(limit).all()
            
            # 관련 Summary 텍스트 가져오기
            summary_texts = []
            for emb in similar_summaries:
                summary = Summary.query.get(emb.summary_id)
                if summary:
                    summary_texts.append(f"{summary.start_date.strftime('%Y-%m-%d')}~{summary.end_date.strftime('%Y-%m-%d')}: {summary.summary_text}")
            
            return summary_texts
        except Exception as e:
            current_app.logger.error(f"Error in _get_similar_summaries: {str(e)}")
            return []

    def get_daily_data(self, user_id: int, select_date: datetime.date) -> Tuple[bool, Optional[Dict], str]:
        """사용자의 일일 데이터 조회
        
        Returns:
            Tuple[bool, Optional[Dict], str]: (성공 여부, 데이터 딕셔너리, 메시지)
        """
        try:
            # Todo 데이터 조회
            todos = Todo.query.filter_by(
                user_id=user_id,
                created_at=select_date
            ).all()
            
            # Diary 데이터 조회
            diary = Diary.query.filter_by(
                user_id=user_id,
                select_date=select_date
            ).first()
            
            # Schedule 데이터 조회
            schedules = Schedule.query.filter_by(
                user_id=user_id,
                created_at=select_date
            ).all()
            
            # 필수 데이터 체크
            if not todos and not diary and not schedules:
                return False, {}, "데이터가 없습니다."
            
            data = {
                'todos': [{'content': todo.content, 'is_completed': todo.is_completed, 'select_date': todo.select_date} for todo in todos],
                'diary': [{'content': diary.content, 'select_date': diary.select_date}],
                'schedules': [{'title': schedule.title, 'content': schedule.content, 'select_date': schedule.select_date} for schedule in schedules]
            }
                
            return True, data, "데이터 조회 성공"
        except Exception as e:
            current_app.logger.error(f"Error in get_daily_data: {str(e)}")
            return False, None, "데이터 조회 중 오류가 발생했습니다."

    def clean_daily_data(self, user_id: int, select_date: datetime.date) -> Tuple[bool, str]:
        """일일 데이터 전처리 및 저장"""
        self._init_model()
        self._init_embedding_service()
        
        try:
            # 데이터 조회
            success, daily_data, message = self.get_daily_data(user_id, select_date)
            if not success:
                return False, message
            
            # 데이터 텍스트 형식으로 변환
            text_content = []

            # 일기 데이터 추가 (select_date 포함)
            text_content.append(f"일기 ({daily_data['diary'][0]['select_date']}): {daily_data['diary'][0]['diary']}" if daily_data['diary'] else "")

            # 할 일 목록 추가
            todo_texts = [f"- {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                        for todo in daily_data['todos']]
            text_content.append("할 일 목록:\n" + "\n".join(todo_texts))

            # 일정 목록 추가 (select_date 포함)
            schedule_texts = [f"- {schedule['title']} ({schedule['select_date']}): {schedule['content']}" 
                            for schedule in daily_data['schedules']]
            text_content.append("일정 목록:\n" + "\n".join(schedule_texts))

            combined_text = "\n\n".join(text_content)       
            
            try:
                # LLM을 통한 텍스트 전처리
                cleaned_text = self._preprocess_text(combined_text)
            except Exception as e:
                current_app.logger.error(f"OpenAI API error: {str(e)}")
                return False, "텍스트 전처리 중 오류가 발생했습니다."
            
            try:
                # CleanedData에 저장
                cleaned_data = CleanedData(
                    user_id=user_id,
                    select_date=select_date,
                    cleaned_text=cleaned_text
                )
                db.session.add(cleaned_data)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
                return False, "데이터 저장 중 오류가 발생했습니다."
            
            return True, cleaned_text
            
        except Exception as e:
            current_app.logger.error(f"Unexpected error in clean_daily_data: {str(e)}")
            return False, "데이터 처리 중 오류가 발생했습니다."

    def get_chat_response(self, user_id: int, question: str) -> Tuple[bool, str]:
        """챗봇 응답 생성"""
        self._init_model()  

        # 사용자 의도 분석
        intent_type, action, content = self._analyze_user_intent(question)
        
        # 원래 의도 저장
        original_type = "todo" if "시에" in question and "할일" in question else None
        
        # 일정이나 할일 관리 요청인 경우
        if intent_type in ["schedule", "todo"] and action in ["add", "update", "delete"]:
            if intent_type == "schedule":
                success, message = self._manage_schedule(user_id, action, content)
                # 원래 할일로 요청했지만 시간이 있어서 일정으로 변환된 경우
                if original_type == "todo":
                    message = f"시간이 포함되어 있어서 할일이 아닌 일정으로 추가했습니다. {message}"
            else:  # todo
                success, message = self._manage_todo(user_id, action, content)
                
            if not success:
                return False, message

        # 기존의 LLM 응답 생성 로직
        contexts = []
        todaydata = []

        # 1. Vector 검색으로 유사한 주간 요약 찾기
        similar_summaries = self._get_similar_summaries(user_id, question)
        if similar_summaries:
            contexts.append("관련된 과거 주간 요약:")
            contexts.extend(similar_summaries)

        # 2. 일일 데이터 조회
        today = datetime.now().date()
        success, daily_data, message = self.get_daily_data(user_id, today)
        if success:
            # 일일 데이터를 컨텍스트에 추가
            if daily_data.get('diary'):
                diary_texts = [f"{diary['select_date']}: {diary['content']}" for diary in daily_data['diary']]
                todaydata.append(f"\n오늘의 데이터:\n" + "\n".join(diary_texts))

            if daily_data.get('todos'):
                todo_texts = [f" {todo['select_date']} : {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                            for todo in daily_data['todos']]
                todaydata.append("오늘의 할 일 목록:\n" + "\n".join(todo_texts))

            if daily_data.get('schedules'):
                schedule_texts = [f"{schedule['select_date']} : {schedule['title']} {schedule['content']}" 
                                for schedule in daily_data['schedules']]
                todaydata.append("오늘의 일정 목록:\n" + "\n".join(schedule_texts))
        else:
            contexts.append(f"일일 데이터가 없습니다. 최소 하루의 데이터를 추가하여야 결과를 얻을 수 있습니다.")

        # 3. 모든 일일 데이터 가져오기
        all_data = CleanedData.query.filter_by(
            user_id=user_id
        ).order_by(CleanedData.select_date.desc()).all()

        if all_data:
            contexts.append("\n과거 데이터:")
            for data in all_data:
                if data.select_date != today:  # 오늘 데이터는임시 제외
                    contexts.append(data.cleaned_text)

        # 일정이나 할일이 변경된 경우 응답 메시지 수정
        if intent_type in ["schedule", "todo"] and action in ["add", "update", "delete"]:
            system_prompt = f"""
            당신은 사용자의 일상을 관리해주는 AI 비서입니다.
            방금 다음과 같은 작업을 수행했습니다: {message}
            
            사용자의 일기, 할 일, 일정 데이터를 기반으로 자연스럽게 대화하며 도움을 제공해주세요.
            항상 친절하고 공감적인 태도를 유지하면서, 실질적인 도움이 되는 답변을 제공해주세요.
            
            오늘의 데이터: {todaydata}
            """
        else:
            system_prompt = f"""
            당신은 사용자의 일상을 관리해주는 AI 비서입니다. 현재는 유저 테스트 단계입니다.
            사용자의 일기, 할 일, 일정 데이터를 기반으로 자연스럽게 대화하며 도움을 제공해주세요.

            유저 테스트를 위해서 데이터들을 자연스럽게 활용하고, 추가적으로 정보를 생각해 내어 대답해 주세요.
            항상 친절하고 공감적인 태도를 유지하면서, 실질적인 도움이 되는 답변을 제공해주세요.
            
            오늘의 데이터: {todaydata}
            """

        # 메시지 구성
        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content="\n".join(contexts)),
            HumanMessage(content=question)
        ]

        try:
            response = self.chat_model.invoke(messages)
            return True, response.content
        except Exception as e:
            current_app.logger.error(f"chat_model.invoke 중 오류 발생: {str(e)}")
            return False, "챗봇 응답 생성 중 오류가 발생했습니다."

    def _parse_date(self, date_str: str) -> datetime.date:
        """날짜 문자열을 파싱하는 메서드"""
        try:
            # 다양한 날짜 형식 처리
            formats = [
                "%Y-%m-%d",
                "%Y년 %m월 %d일",
                "%m월 %d일",
                "오늘",
                "내일",
                "모레"
            ]
            
            if date_str in ["오늘", "today"]:
                return datetime.now().date()
            elif date_str in ["내일", "tomorrow"]:
                return (datetime.now() + timedelta(days=1)).date()
            elif date_str in ["모레", "day after tomorrow"]:
                return (datetime.now() + timedelta(days=2)).date()
            
            for fmt in formats:
                try:
                    if "년" not in date_str and fmt == "%Y년 %m월 %d일":
                        continue
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    if "년" not in date_str:
                        # 년도가 없는 경우 현재 년도 사용
                        parsed_date = parsed_date.replace(year=datetime.now().year)
                    return parsed_date
                except ValueError:
                    continue
            
            raise ValueError("지원하지 않는 날짜 형식입니다.")
        except Exception as e:
            raise ValueError(f"날짜 파싱 오류: {str(e)}")

    def _parse_time(self, time_str: str) -> datetime.time:
        """시간 문자열을 파싱하는 메서드"""
        try:
            # 24시간 형식으로 변환
            if "오후" in time_str:
                hour = int(time_str.replace("오후", "").replace("시", "").strip())
                if hour != 12:
                    hour += 12
            elif "오전" in time_str:
                hour = int(time_str.replace("오전", "").replace("시", "").strip())
                if hour == 12:
                    hour = 0
            else:
                hour = int(time_str.replace("시", "").strip())
            
            return datetime.strptime(f"{hour}:00", "%H:%M").time()
        except Exception as e:
            raise ValueError(f"시간 파싱 오류: {str(e)}")

    def _find_schedule(self, user_id: int, content: dict) -> Optional[Schedule]:
        """일정을 찾는 메서드"""
        try:
            if "schedule_id" in content:
                return Schedule.query.filter_by(user_id=user_id, id=content["schedule_id"]).first()
            
            # 날짜, 시간, 제목으로 찾기
            query = Schedule.query.filter_by(user_id=user_id)
            
            if "date" in content:
                query = query.filter_by(select_date=self._parse_date(content["date"]))
            
            if "time" in content:
                if isinstance(content["time"], str):
                    if ":" in content["time"]:
                        time = datetime.strptime(content["time"], "%H:%M").time()
                    else:
                        time = self._parse_time(content["time"])
                    query = query.filter_by(time=time)
            
            if "title" in content:
                query = query.filter_by(title=content["title"])
            
            return query.first()
        except Exception:
            return None

    def _find_todo(self, user_id: int, content: dict) -> Optional[Todo]:
        """할일을 찾는 메서드"""
        try:
            if "todo_id" in content:
                return Todo.query.filter_by(user_id=user_id, id=content["todo_id"]).first()
            
            # 날짜와 내용으로 찾기
            query = Todo.query.filter_by(user_id=user_id)
            
            if "date" in content:
                query = query.filter_by(select_date=self._parse_date(content["date"]))
            
            if "content" in content:
                query = query.filter_by(content=content["content"])
            
            return query.first()
        except Exception:
            return None

    def _manage_schedule(self, user_id: int, action: str, content: dict) -> Tuple[bool, str]:
        """일정 관리 메서드"""
        try:
            if action == "add":
                # 시간 정보 파싱
                time_str = content.get("time", "12:00")
                if isinstance(time_str, str):
                    if ":" in time_str:
                        parsed_time = datetime.strptime(time_str, "%H:%M").time()
                    else:
                        parsed_time = self._parse_time(time_str)
                else:
                    parsed_time = datetime.strptime("12:00", "%H:%M").time()

                schedule = Schedule(
                    user_id=user_id,
                    title=content["title"],
                    content=content.get("content", ""),
                    select_date=self._parse_date(content["date"]),
                    time=parsed_time
                )
                db.session.add(schedule)
                message = "일정이 추가되었습니다."
            
            elif action == "update":
                schedule = self._find_schedule(user_id, content)
                if not schedule:
                    return False, "해당 일정을 찾을 수 없습니다."
                
                if "title" in content:
                    schedule.title = content["title"]
                if "content" in content:
                    schedule.content = content["content"]
                if "date" in content:
                    schedule.select_date = self._parse_date(content["date"])
                if "time" in content:
                    if isinstance(content["time"], str):
                        if ":" in content["time"]:
                            schedule.time = datetime.strptime(content["time"], "%H:%M").time()
                        else:
                            schedule.time = self._parse_time(content["time"])
                message = "일정이 수정되었습니다."
            
            elif action == "delete":
                schedule = self._find_schedule(user_id, content)
                if not schedule:
                    return False, "해당 일정을 찾을 수 없습니다."
                
                db.session.delete(schedule)
                message = "일정이 삭제되었습니다."
            
            db.session.commit()
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"일정 관리 중 오류가 발생했습니다: {str(e)}"

    def _manage_todo(self, user_id: int, action: str, content: dict) -> Tuple[bool, str]:
        """할일 관리 메서드"""
        try:
            if action == "add":
                todo = Todo(
                    user_id=user_id,
                    content=content["content"],
                    select_date=self._parse_date(content["date"]),
                    is_completed=content.get("is_completed", False)
                )
                db.session.add(todo)
                message = "할일이 추가되었습니다."
            
            elif action == "update":
                todo = self._find_todo(user_id, content)
                if not todo:
                    return False, "해당 할일을 찾을 수 없습니다."
                
                if "content" in content:
                    todo.content = content["content"]
                if "date" in content:
                    todo.select_date = self._parse_date(content["date"])
                if "is_completed" in content:
                    todo.is_completed = content["is_completed"]
                message = "할일이 수정되었습니다."
            
            elif action == "delete":
                todo = self._find_todo(user_id, content)
                if not todo:
                    return False, "해당 할일을 찾을 수 없습니다."
                
                db.session.delete(todo)
                message = "할일이 삭제되었습니다."
            
            db.session.commit()
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"할일 관리 중 오류가 발생했습니다: {str(e)}"

    def _analyze_user_intent(self, question: str) -> Tuple[str, str, dict]:
        """사용자 의도 분석"""
        self._init_model()
        
        system_prompt = """
        당신은 사용자의 의도를 분석하는 AI 비서입니다.
        사용자의 메시지를 분석하여 다음 정보를 JSON 형식으로 반환해주세요:
        1. type: "schedule" 또는 "todo" 또는 "chat"
        2. action: "add", "update", "delete", 또는 "chat"
        3. content: 관련 정보를 담은 딕셔너리

        중요한 규칙:
        - 시간이 언급된 경우(예: "2시", "오후 3시", "13시" 등) 반드시 type을 "schedule"로 설정하세요.
        - schedule type인 경우 반드시 title과 time을 포함해야 합니다.
        - todo type인 경우 시간 정보를 포함하지 않습니다.
        - 삭제나 수정 요청 시 일정/할일을 찾는데 필요한 모든 정보(날짜, 시간, 제목/내용)를 포함해야 합니다.
        
        예시:
        - "내일 2시에 미팅 일정 추가해줘" -> {"type": "schedule", "action": "add", "content": {"title": "미팅", "date": "내일", "time": "14:00"}}
        - "오늘 오후 3시에 보고서 작성하기" -> {"type": "schedule", "action": "add", "content": {"title": "보고서 작성", "date": "오늘", "time": "15:00"}}
        - "오늘 17시 운동 일정 삭제해줘" -> {"type": "schedule", "action": "delete", "content": {"title": "운동", "date": "오늘", "time": "17:00"}}
        - "오늘 할일에 보고서 작성 추가해줘" -> {"type": "todo", "action": "add", "content": {"content": "보고서 작성", "date": "오늘"}}
        - "오늘 할일 중에서 보고서 작성 삭제해줘" -> {"type": "todo", "action": "delete", "content": {"content": "보고서 작성", "date": "오늘"}}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        
        response = self.chat_model.invoke(messages)
        
        try:
            import json
            result = json.loads(response.content)
            
            # 시간이 포함된 경우 schedule로 변환
            if result["type"] == "todo" and ("time" in result["content"] or 
                any(time_indicator in question for time_indicator in ["시에", "시까지", "시부터"])):
                result["type"] = "schedule"
                if "content" in result["content"]:
                    result["content"]["title"] = result["content"].pop("content")
                if "time" not in result["content"]:
                    # 시간 정보 추출 (기본값 설정)
                    result["content"]["time"] = "12:00"
            
            return result["type"], result["action"], result["content"]
        except Exception as e:
            current_app.logger.error(f"의도 분석 중 오류 발생: {str(e)}")
            return "chat", "chat", {}

    def create_feedback(self, user_id: int, select_date: datetime.date) -> Tuple[bool, str]:
        """일일 피드백 생성"""
        self._init_model()
        
        # 컨텍스트 수집
        contexts = []
        todaydata = []
        
        # 1. 모든 주간 요약 가져오기
        summaries = Summary.query.filter_by(
            user_id=user_id,
            type='weekly'
        ).order_by(Summary.end_date.desc()).limit(3).all()
        
        if summaries:
            contexts.append("주간 요약:")
            for summary in summaries:
                contexts.append(f"{summary.start_date.strftime('%Y-%m-%d')}~{summary.end_date.strftime('%Y-%m-%d')}: {summary.summary_text}")
        
        # 2. 일일 데이터 조회
        today = datetime.now().date()
        success, daily_data, message = self.get_daily_data(user_id, today)
        if success:
            # 일일 데이터를 컨텍스트에 추가
            if daily_data.get('diary'):
                diary_texts = [f"{diary['select_date']}: {diary['content']}" for diary in daily_data['diary']]
                todaydata.append(f"\n오늘의 데이터:\n" + "\n".join(diary_texts))

            if daily_data.get('todos'):
                todo_texts = [f" {todo['select_date']} : {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                            for todo in daily_data['todos']]
                todaydata.append("오늘의 할 일 목록:\n" + "\n".join(todo_texts))

            if daily_data.get('schedules'):
                schedule_texts = [f"{schedule['select_date']} : {schedule['title']} {schedule['content']}" 
                                for schedule in daily_data['schedules']]
                todaydata.append("오늘의 일정 목록:\n" + "\n".join(schedule_texts))

        else:
            contexts.append(f"일일 데이터가 없습니다. 최소 하루의 데이터를 추가하여야 결과를 얻을 수 있습니다.")

        
        # 3. 모든 일일 데이터 가져오기
        all_data = CleanedData.query.filter_by(
            user_id=user_id
        ).order_by(CleanedData.select_date.desc()).all()

        if all_data:
            contexts.append("\n과거 데이터:")
            for data in all_data:
                if data.select_date != today:  # 오늘 데이터는임시 제외
                    contexts.append(f"{data.select_date.strftime('%Y-%m-%d')}의 데이터:\n{data.cleaned_text}")
        

        # 유저 테스트용
        system_prompt = f"""
            사용자의 하루 데이터를 분석하여 다음과 같은 피드백을 제공해주세요:
            1. 할 일 완료율과 성취도 분석
            2. 긍정적인 부분 강조
            3. 개선이 필요한 부분에 대한 건설적인 제안
            4. 전반적인 하루 평가와 격려의 메시지

            피드백은 항상 긍정적이고 동기부여가 되는 톤을 유지하면서, 구체적이고 실천 가능한 제안을 포함해야 합니다.

            현재는 유저테스트 단계입니다.

            피드백은 오늘하루가 어땟는지 오늘의 데이터의 평가만을 해야합니다. 
            데이터를 반환하지말고, 오늘의 데이터에 대한 평가만을 적어줘.
            

            오늘의 데이터야. {todaydata}
            간단하게 1~2줄로 답변해주세요.
            """
        
        # 메시지 구성: 시스템 프롬프트와 컨텍스트
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(contexts))
        ]

        try:
            response = self.chat_model.invoke(messages)
            feedback_text = response.content

            # Feedback 모델에 저장
            feedback = Feedback(
                user_id=user_id,
                feedback=feedback_text,
                select_date=select_date
            )
            db.session.add(feedback)
            db.session.commit()

            return True, feedback_text
        except Exception as e:
            current_app.logger.error(f"Error in create_feedback: {str(e)}")
            return False, "피드백 생성 중 오류가 발생했습니다."

    def create_recommendation(self, user_id: int) -> Tuple[bool, str]:
        """일정 추천 생성"""
        self._init_model()
        
        # 컨텍스트 수집
        contexts = []
        todaydata = []
        
        # 1. 모든 주간 요약 가져오기
        summaries = Summary.query.filter_by(
            user_id=user_id,
            type='weekly'
        ).order_by(Summary.end_date.desc()).limit(3).all()
        
        if summaries:
            contexts.append("주간 요약:")
            for summary in summaries:
                contexts.append(f"{summary.start_date.strftime('%Y-%m-%d')}~{summary.end_date.strftime('%Y-%m-%d')}: {summary.summary_text}")
        

        # 2. 일일 데이터 조회
        today = datetime.now().date()
        success, daily_data, message = self.get_daily_data(user_id, today)
        if success:
            # 일일 데이터를 컨텍스트에 추가
            if daily_data.get('diary'):
                diary_texts = [f"{diary['select_date']}: {diary['content']}" for diary in daily_data['diary']]
                todaydata.append(f"\n오늘의 데이터:\n" + "\n".join(diary_texts))

            if daily_data.get('todos'):
                todo_texts = [f" {todo['select_date']} : {todo['content']} ({'완료' if todo['is_completed'] else '미완료'})" 
                            for todo in daily_data['todos']]
                todaydata.append("오늘의 할 일 목록:\n" + "\n".join(todo_texts))

            if daily_data.get('schedules'):
                schedule_texts = [f"{schedule['select_date']} : {schedule['title']} {schedule['content']}" 
                                for schedule in daily_data['schedules']]
                todaydata.append("오늘의 일정 목록:\n" + "\n".join(schedule_texts))

        else:
            contexts.append(f"일일 데이터가 없습니다. 최소 하루의 데이터를 추가하여야 결과를 얻을 수 있습니다.")

        
        # 3. 모든 일일 데이터 가져오기
        all_data = CleanedData.query.filter_by(
            user_id=user_id
        ).order_by(CleanedData.select_date.desc()).all()
        
        if all_data:
            contexts.append("\n과거 데이터:")
            for data in all_data:
                if data.select_date != today:  # 오늘 데이터는임시 제외
                    contexts.append(f"{data.select_date.strftime('%Y-%m-%d')}의 데이터:\n{data.cleaned_text}")
        

        # 유저 테스트용
        system_prompt = f"""
            사용자의 하루 데이터를 분석하여 다음과 같은 추천을 제공해주세요:
            1. 현재 일정과 할 일을 고려한 시간 관리 제안
            2. 업무/학습 효율을 높일 수 있는 활동 추천
            3. 스트레스 해소와 휴식을 위한 활동 제안
            4. 사용자의 관심사와 목표를 고려한 새로운 활동 추천

            현재는 유저테스트 단계입니다.

            깔끔하게 정리답변해줘야해.
            오늘 일정같은거 보여주지말고 딱 추천만.
            
            오늘의 데이터야. {todaydata}
            간단하게 1~2줄로 답변해줘.

        """
        
        # 메시지 구성: 시스템 프롬프트와 컨텍스트
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(contexts))
        ]
        
        response = self.chat_model.invoke(messages)
        return True, response.content

    def _preprocess_text(self, text: str) -> str:
        """LLM을 사용한 텍스트 전처리"""
        system_prompt = """
        입력된 텍스트를 자연스럽게 정리해주세요. 
        중요한 내용은 유지하면서, 불필요한 부분은 제거하고 문장을 매끄럽게 다듬어주세요.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=text)
        ]
        
        response = self.chat_model.invoke(messages)
        return response.content