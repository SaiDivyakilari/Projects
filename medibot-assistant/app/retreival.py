from app.config import *
from app import config
from qdrant_client import  models
from langchain_core.documents import Document
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from typing import List



class Retrieval:

    def __init__(self):
        self.dense_embeddings = DENSE_EMBEDDINGS
        self.sparse_embeddings = SPARSE_EMBEDDINGS
        self.client = QDRANT_CLIENT
        self.cross_encoder = HuggingFaceCrossEncoder(model_name=CROSS_ENCODER_MODEL)
        self.reranker = CrossEncoderReranker(model=self.cross_encoder, top_n=TOP_K)
    


    def embedding_query(self,query : str):

        dense_vecs = self.dense_embeddings.embed_query(query)
        sparse_vecs = self.sparse_embeddings.embed_query(query)
        return dense_vecs, sparse_vecs

    @staticmethod
    def role_filter(role: str) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="access_roles",
                    match=models.MatchAny(any=[role]),
                )
            ]
        )

    def get_relevant_documents(self,dense_vecs, sparse_vecs,role : str):
        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(query=dense_vecs, using="dense", limit=DENSE_LIMIT),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vecs.indices,
                        values=sparse_vecs.values,
                    ),
                    using="sparse",
                    limit=SPARSE_LIMIT,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=self.role_filter(role),
            limit=COMBINED_LIMIT,

            with_payload=True,
        ).points
        

        return [
                    Document(
                        page_content=r.payload["text"],
                        metadata={k: v for k, v in r.payload.items() if k != "text"},
                    )
                    for r in results
                ]

    def retrieve(self, query: str, role: str) -> List[Document]:
        dense, sparse = self.embedding_query(query)
        candidates = self.get_relevant_documents(dense, sparse, role)
        if not candidates:
            return []

        # relevance gate
        best = max(self.cross_encoder.score([(query, d.page_content) for d in candidates]))
        if best < RELEVANCE_THRESHOLD:
            return []

        # reranking via the LangChain compressor
        return self.reranker.compress_documents(candidates, query)




if __name__ == "__main__":
    r = Retrieval()
    print(r.retrieve("How do I apply for annual leave?", "nurse"))
    print(r.retrieve("On what basis billing is done", "billing_executive"))




    



