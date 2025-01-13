"""
llm 구현
"""


# app/utils/llm_service.py

import openai
from typing import List
from decouple import config
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.vectorstores import PGVector
from langchain.embeddings import OpenAIEmbeddings
from flask import current_app
    


# OpenAI API 키 설정
openai.api_key = config("OPENAI_API_KEY")

class LLMService:
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.llm = OpenAI(model_name = model_name, temperature = 0.5)
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = PGVector(
            connection_string = config("SQLALCHEMY_DATABASE_URI"),
            embedding_dimension = 1536,
            collection_name = "ai_responses"
        )
        self.qa_chain = RetrievalQA.from_chain_type(
            llm = self.llm,
            chain_type = "stuff",
            retrieval = self.vector_store.as_retrieval(search_kwargs = {"k": 5}),
            return_source_documents = True
        )

    
    def generate_direct_response(self, prompt: str) -> str:
        """
        직접적인 질문에 대한 답변 생성
        """
        try:
            response = openai.Completion.create(
                engine = "gpt-4o-mini",
                prompt = prompt,
                max_tokens = 150,
                temperature = 0.7
            )
            return response.choices[0].text.strip()
        except Exception as e:
            current_app.logger.error(f"직접적인 질문에 대한 답변 생성 중 오류 발생: {e}")
            return "직접적인 질문에 대한 답변 생성 중 오류 발생"

    
    def summarize_text(self, text: str) -> str:
        """
        텍스트 요약, 키워드 추출
        """
        try:
            prompt = f"다음 주어진 텍스트를 요약하거나 핵심 키워드만 뽑아줘 : \n{text}\n\n요약:"
            response = openai.api_key.create_completion(
                engine = "gpt-4o-mini",
                prompt = prompt,
                max_tokens = 200,
                temperature = 0.3
            )
            summary = response.choices[0].text.strip()
            return summary
        except Exception as e:
            current_app.logger.error(f"텍스트 요약 중 오류 발생: {e}")
            return "요약 중 오류 발생"


    
    def generate_response(self, summaries: List[str], query: str) -> str:
        """
        요약된 텍스트를 참고하여서 prompt를 생성
        """
        try:
            response = self.qa_chain.run(query)
            return response
        except Exception as e:
            current_app.logger.error(f"요약된 텍스트를 참고하여서 prompt 생성 중 오류 발생: {e}")
            return "요약된 텍스트를 참고하여서 prompt 생성 중 오류 발생"
        


    def embed_text(self, text: str) -> List[float]:
        """
        텍스트를 Embedding으로 변환
        """
        try:
            response = openai.Embedding.create(
                input = text,
                model = "text-embedding-3-small"
            )
            embedding = response['data'][0]['embedding']

            return embedding
        except Exception as e:
            current_app.logger.error(f"텍스트를 Embedding으로 변환 중 오류 발생: {e}")
            return []

