from flask import Blueprint, request, jsonify
from app.utils.llm_service import LLMService

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route("/", methods=["POST"])
def chatbot():
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
        'message': '응답이 성공적으로 생성되었습니다',
        'data': {
            'response': response
        }
    })
