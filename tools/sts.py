import os
import sys
import pandas as pd
import numpy as np
# from xinference.client import Client
from xinference_client import RESTfulClient as Client
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(os.path.dirname(__file__))
from config import base_config


class STS:
    def __init__(self, similarity_threshold=0.75):
        client = Client(base_config.llm_url)
        self.model = client.get_model("bge-large-zh-v1.5")
        base_service_words = os.path.join(os.path.dirname(__file__), '..', base_config.base_autocomplete)
        sheet = pd.read_excel(base_service_words)
        self.sts = {}
        for key in sheet.columns:
            value = sheet[key].dropna().tolist()
            _embeddings = self.model.create_embedding(value)["data"]
            embeddings = np.array([data["embedding"] for data in _embeddings])
            self.sts[key] = {"context": value, "embedding": embeddings}
        self.similarity_threshold = similarity_threshold

    def SetKeywords(self, input):
        sts_new = {}
        for key in input.keys():
            contexts, embeddings = [], []
            if key in self.sts.keys():
                for text in input[key]:
                    contexts.append(text)
                    if text in self.sts[key]["context"]:
                        idx = self.sts[key]["context"].index(text)
                        embedding = self.sts[key]["embedding"][idx]
                    else:
                        embedding = np.array(self.model.create_embedding(text)["data"][0]["embedding"])
                    embeddings.append(embedding)
            else:
                for text in input[key]:
                    contexts.append(text)
                    embedding = np.array(self.model.create_embedding(text)["data"][0]["embedding"])
                    embeddings.append(embedding)
            embeddings = np.array(embeddings)
            sts_new[key] = {"context": contexts, "embedding": np.array(embeddings)}
        self.sts = sts_new

    def get_top_context(self, query, query_length=4, top_k=3):
        sts_word = []
        if len(query) >= query_length:
            cur_embedding = self.model.create_embedding(query)
            cur_embedding = np.array(cur_embedding["data"][0]["embedding"]).reshape(1, -1)
            for key in self.sts.keys():
                contexts = np.array(self.sts[key]["context"])
                similaritys = cosine_similarity(cur_embedding, self.sts[key]["embedding"])[0]
                indices = np.where(similaritys > self.similarity_threshold)
                filtered_contexts = contexts[indices]
                filtered_similarities = similaritys[indices]
                similarity_rank = np.argsort(-filtered_similarities)[:top_k]
                for idx in similarity_rank:
                    sts_word.append(
                        {"type": key, "context": filtered_contexts[idx],
                         "similarity": round(filtered_similarities[idx], 2)})
        return sts_word
