from flask import Blueprint, request, jsonify
from app.utils.chatbot_function import ChatbotFunctions
from app.utils.llm_service import LLMService
from datetime import datetime
from app.models import Schedule, Todo, Diary

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route("/", methods=["POST"])
def chatbot():
    """챗봇 응답 생성 API"""
    data = request.get_json()
    user_id = data.get('user_id')
    question = data.get('question')
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    if not question:
        return jsonify({'success': False, 'message': '질문을 입력해주세요.'}), 400
    
    llm_service = LLMService()
    success, response = llm_service.get_chat_response(user_id, question)
    
    if not success:
        return jsonify({'success': False, 'message': response}), 400
        
    return jsonify({
        'success': True,
        'message': '응답 생성 성공',
        'data': {
            'response': response
        }
    })

@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data['user_id']
    question = data['question']

    chatbot_functions = ChatbotFunctions()
    return chatbot_functions.process_chat(user_id, question)
