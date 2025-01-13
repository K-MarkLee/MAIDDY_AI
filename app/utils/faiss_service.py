# app/utils/faiss_service.py

import faiss
import numpy as np
import pickle
import os
from flask import current_app

class FAISSService:
    def __init__(self, embedding_dim=768, index_dir='faiss_indexes'):
        self.embedding_dim = embedding_dim
        self.index_dir = index_dir
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

    def get_index_path(self, user_id):
        """특정 사용자의 FAISS 인덱스 경로를 반환."""
        return os.path.join(self.index_dir, f'faiss_{user_id}.index')

    def get_summary_ids_path(self, user_id):
        """특정 사용자의 요약 ID 파일 경로를 반환."""
        return os.path.join(self.index_dir, f'faiss_{user_id}.summary_ids')

    def initialize_index(self, user_id):
        """특정 사용자용 FAISS 인덱스 초기화."""
        index = faiss.IndexFlatL2(self.embedding_dim)
        faiss.write_index(index, self.get_index_path(user_id))
        # 빈 summary_ids 리스트 초기화
        with open(self.get_summary_ids_path(user_id), 'wb') as f:
            pickle.dump([], f)
        return index

    def load_index(self, user_id):
        """특정 사용자의 FAISS 인덱스 로드."""
        index_path = self.get_index_path(user_id)
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
        else:
            index = self.initialize_index(user_id)
        return index

    def load_summary_ids(self, user_id):
        """특정 사용자의 요약 ID 로드."""
        summary_ids_path = self.get_summary_ids_path(user_id)
        if os.path.exists(summary_ids_path):
            with open(summary_ids_path, 'rb') as f:
                summary_ids = pickle.load(f)
        else:
            summary_ids = []
        return summary_ids

    def save_summary_ids(self, user_id, summary_ids):
        """특정 사용자의 요약 ID 저장."""
        summary_ids_path = self.get_summary_ids_path(user_id)
        with open(summary_ids_path, 'wb') as f:
            pickle.dump(summary_ids, f)

    def add_embedding(self, embedding, user_id, summary_id):
        """사용자의 FAISS 인덱스에 임베딩과 요약 ID 추가."""
        index = self.load_index(user_id)
        embedding_np = np.array([embedding]).astype('float32')
        index.add(embedding_np)
        faiss.write_index(index, self.get_index_path(user_id))
        
        # summary_ids 업데이트
        summary_ids = self.load_summary_ids(user_id)
        summary_ids.append(summary_id)
        self.save_summary_ids(user_id, summary_ids)

    def search(self, query_embedding, user_id, top_k=10):
        """사용자의 FAISS 인덱스에서 유사한 상위 k개의 요약 ID 검색."""
        index = self.load_index(user_id)
        query_np = np.array([query_embedding]).astype('float32')
        distances, indices = index.search(query_np, top_k)
        
        summary_ids = self.load_summary_ids(user_id)
        results = []
        for idx in indices[0]:
            if idx < len(summary_ids):
                results.append(summary_ids[idx])
        return distances[0], results  # distances와 summary_ids를 반환
