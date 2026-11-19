import os
import json
import boto3
from dotenv import load_dotenv
import sys
from pathlib import Path

from httpx2 import get
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



from app.config import get_settings

settings = get_settings()
print(settings.EMBED_DIMENSION)

load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# Test 1: Amazon Titan Embeddings
embedding_response = client.invoke_model(
    modelId= settings.BEDROCK_EMBED_MODEL,
    body=json.dumps({
        "inputText": "Hello Amazon Bedrock",
        "dimensions": settings.EMBED_DIMENSION,
        "normalize": True
    }),
    contentType="application/json",
    accept="application/json"
)

embedding_data = json.loads(
    embedding_response["body"].read()
)

print("Embedding dimension:", len(embedding_data["embedding"]))

# Test 2: Amazon Nova Lite
chat_response = client.converse(
    modelId= settings.BEDROCK_CHAT_MODEL,
    messages=[
        {
            "role": "user",
            "content": [
                {"text": "Explain RAG in one sentence."}
            ]
        }
    ],
    inferenceConfig={"maxTokens": 200}
)

print(
    "Nova Response:",
    chat_response["output"]["message"]["content"][0]["text"]
)