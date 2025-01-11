"""
llm 구현
"""


# app/utils/llm_service.py

import openai
from decouple import config

# OpenAI API 키 설정
OPENAI_API_KEY = config("OPENAI_API_KEY", "")
openai.api_key = OPENAI_API_KEY

class LLMService:
    def __init__(self, model_name="gpt-3.5-turbo"):
        # LangChain의 OpenAI LLM 래퍼
        self.llm = OpenAI(model_name=model_name, openai_api_key=OPENAI_API_KEY)
        
    
    def generate_direct_response(self, prompt: str) -> str:
        """
        간단히 prompt -> 답변
        """
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].text.strip()

    def summarize_text(self, text: str) -> str:
        """
        텍스트를 요약 또는 키워드 추출
        """
        prompt = f"다음 텍스트를 요약하거나 핵심 키워드만 뽑아줘:\n{text}\n"
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=200,
            temperature=0.3
        )
        summary = response.choices[0].text.strip()
        return summary

    def generate_response(self, query: str, summarized_texts: list[str]) -> str:
        """
        LLM을 사용하여 답변 생성
        """
        combined_text = "/n".join(summarized_texts)
        prompt = f"다음 요약된 내용들을 참고하여 질문에 답변해줘:\n{combined_text}\n\n질문: {query}\n답변:"
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            temperature=0.5
        )
        response = response.choices[0].text.strip()
        return response

# FAISS를 써야해?