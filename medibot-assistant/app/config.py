import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Set the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'Data'
DB_PATH = DATA_DIR / 'db' / 'mediassist.db'

# Define model names for different tasks
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = "openai/gpt-oss-20b" 

# Define the path for the Qdrant client and the collection name
QUDRANT_CLIENT_PATH = BASE_DIR / 'qudrant_client'
COLLECTION_NAME = "mediassist"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import FastEmbedSparse
from qdrant_client import QdrantClient

DENSE_EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
SPARSE_EMBEDDINGS = FastEmbedSparse(model_name=SPARSE_MODEL)
QDRANT_CLIENT = QdrantClient(path=str(QUDRANT_CLIENT_PATH))

# LLM model configuration
LLM_MODEL_CONFIG = {
    "model": LLM_MODEL,
    "temperature": 0,
    "max_tokens": 512,# make sure to adjust this based on your needs and the model's capabilities

}

MAX_TOKENS = 512

TOP_K = 3
DENSE_LIMIT = 20
SPARSE_LIMIT = 10
COMBINED_LIMIT = 5
RELEVANCE_THRESHOLD = -0.8

# Roles COnfiguration
ROLES = {
    "general" : ['doctor','nurse','billing_executive','technician','admin'],
    "nursing" :['nurse','doctor','admin'],
    "clinical" : ["doctor", "admin"],
    "billing" : ["billing_executive", "admin"],
    "equipment" : ["technician", "admin"]
}

DB_ROLES = {"billing_executive", "admin"}