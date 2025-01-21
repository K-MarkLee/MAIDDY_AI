# MAIDDY_AI/app/routes/feedback.py

from flask import Blueprint, request, jsonify
from app.utils.llm_service import LLMService
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route("/", methods=["POST"])
def create_feedback():
    """일일 피드백 생성 API"""
    data = request.get_json()
    user_id = data.get('user_id')
    date_str = data.get('select_date')  # YYYY-MM-DD 형식
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    try:
        select_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': '올바른 날짜 형식이 아닙니다. (YYYY-MM-DD)'}), 400
    
    llm_service = LLMService()
    success, response = llm_service.create_feedback(user_id, select_date)
    
    if not success:
        return jsonify({'success': False, 'message': response}), 400
        
    return jsonify({
        'success': True,
        'message': '피드백 생성 성공',
        'data': {
            'feedback': response
        }
    })
