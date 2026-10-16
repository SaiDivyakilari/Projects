from app.config import *

from pathlib import Path
from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument
from hierarchical.postprocessor import ResultPostprocessor
from docling.chunking import HybridChunker
from transformers import AutoTokenizer
from langchain_core.documents import Document
from typing import List
from qdrant_client import QdrantClient, models
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import FastEmbedSparse
from qdrant_client.models import Distance, VectorParams
import uuid

SUPPORTED_SUFFIXES = {".pdf", ".md"}


class Medibot_Ingestion:

    def __init__(self):
        self.data_dir = DATA_DIR
        self.db_dir = DB_PATH
        self.collection = COLLECTION_NAME

        self.converter = DocumentConverter() 
        self.tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
        self.chunker = HybridChunker(tokenizer = self.tokenizer, max_tokens = MAX_TOKENS, merge_peers = True)

        self.client = QDRANT_CLIENT
        self.Dense_embeddings = DENSE_EMBEDDINGS
        self.Sparse_embeddings = SPARSE_EMBEDDINGS



    # Loading the document
    def load_document(self,source_file : Path) -> DoclingDocument | None:
        """
        Load a document from the specified source path.

        Args:
            source_file (str): The path to the document file.
        """
        # check if the source file exists
        try :
            #create an instance of DocumentConverter
            converter = self.converter

            # Load the document using the converter
            result = converter.convert(source_file)

            # Postprocessing the document
            ResultPostprocessor(result).process()

            return result.document
        
        except Exception as exc:
            print(f"Error loading document: {exc}")
            return None

    # chunking the document
    def chunk_document(self,document : DoclingDocument) -> List:

        chunks = list(self.chunker.chunk(document))
        return chunks

    # creating the a list of langchain documents for every chunk
    def document_arranging(self,chunks : List, source_file : Path) -> List[Document]:
        source_file = Path(source_file)
        collection = source_file.parent.name        # getting the names of the pdf folders
        access_roles = ROLES[collection]

        pdf_docs : List[Document] = []

        for chunk in chunks:
            headings = chunk.meta.headings or []
            doc = Document(
                page_content = self.chunker.contextualize(chunk=chunk),
                metadata = {
                    "source_document" : source_file.name,
                    "collection" : collection,
                    "access_roles" :access_roles,
                    "section_title" : headings[-1] if headings else None,
                    "chunk_type" : self._chunk_type(chunk),
                    "text" : self.chunker.contextualize(chunk=chunk),
                    "page": self._page(chunk),
                },)
            
            pdf_docs.append(doc)

        return pdf_docs

    @staticmethod
    def _chunk_type(chunk) -> str:

        try : 
            label = str(chunk.meta.doc_items[0].label).lower()

        except Exception as e:
            print(f"Unable to find the chunk label")
            print(f" Raised exception : {e}")
            return "text"

        if "table" in label:
            return "table"
        if "header" in label or "title" in label:
            return "heading"
        if "code" in label:
            return "code"
        return "text"

    @staticmethod
    def _page(chunk) -> int | None:
        try:
            return chunk.meta.doc_items[0].prov[0].page_no
        except Exception as e:
            return None


    def setup_collection(self)-> None :

        # finding if the collection exists and if it exists deleting it
        if self.client.collection_exists(self.collection):
            print(f"Collection '{self.collection}' exists — deleting it.")
            self.client.delete_collection(self.collection)

        vector_size = len(self.Dense_embeddings.embed_query("probe"))

        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )

        # Indexed so the RBAC filter runs inside the search, not after it.
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="access_roles",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="collection",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

        print(f"Created collection '{self.collection}' (dim={vector_size}).")


    # ------------------------------------------------------------------
    # embedding and indexing
    # ------------------------------------------------------------------

    def embed_upsert(self, pdf_docs: List[Document]) -> int:

        if not pdf_docs:
            return 0

        dense_vecs = self.Dense_embeddings.embed_documents([doc.page_content for doc in pdf_docs])
        sparse_vecs = self.Sparse_embeddings.embed_documents([doc.page_content for doc in pdf_docs])

        points = []

        for i, doc in enumerate(pdf_docs):
            point = models.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dense_vecs[i],
                    "sparse": models.SparseVector(
                        indices=sparse_vecs[i].indices,
                        values=sparse_vecs[i].values,
                    ),
                },
                payload={
                    **doc.metadata,
                },
            )
            points.append(point)

        self.client.upsert(collection_name=self.collection, points=points, wait=True)
        print(self.client.count(self.collection))
        return len(points)

    def ingest_file(self, source_file: Path) -> int:
        document = self.load_document(source_file)
        if document is None:
            return 0

        chunks = self.chunk_document(document)
        if not chunks:
            print(f"[warn] {source_file.name}: no chunks produced")
            return 0

        pdf_docs = self.document_arranging(chunks, source_file)
        return self.embed_upsert(pdf_docs)

    def ingest_all(self) -> None:
        self.setup_collection()

        total = 0
        for collection in ROLES:
            folder = self.data_dir / collection

            for path in sorted(folder.iterdir()):
                if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                    continue

                n = self.ingest_file(path)
                total += n
                print(f"{collection}/{path.name}: {n} chunks")

        print(f"\nDone — {total} chunks indexed.")


if __name__ == "__main__":
    Medibot_Ingestion().ingest_all()