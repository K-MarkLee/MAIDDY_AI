# MAIDDY_AI/app/routes/recommend.py

from flask import Blueprint, request, jsonify
from app.utils.llm_service import LLMService

recommend_bp = Blueprint('recommend', __name__)

@recommend_bp.route("/", methods=["POST"])
def create_recommendation():
    """일정 추천 생성 API"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    llm_service = LLMService()
    success, response = llm_service.create_recommendation(user_id)
    
    if not success:
        return jsonify({'success': False, 'message': response}), 400
    
    return jsonify({
        'success': True,
        'message': '추천 생성 성공',
        'data': {
            'recommendation': response
        }
    })
