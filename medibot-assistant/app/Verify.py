
from qdrant_client import QdrantClient, models
from app.config import COLLECTION_NAME, QDRANT_CLIENT_PATH ,  ROLES

client = QdrantClient(path=str(QDRANT_CLIENT_PATH ))

print(client.count(COLLECTION_NAME).count)

pt = client.scroll(COLLECTION_NAME, limit=1, with_payload=True)[0][0]
print(pt.payload)

# per collection — iterate the keys
for collection in ROLES:
    n = client.count(COLLECTION_NAME, count_filter=models.Filter(must=[
        models.FieldCondition(key="collection", match=models.MatchValue(value=collection))
    ])).count
    print(f"{collection}: {n} chunks")

# per role — iterate the distinct values
all_roles = sorted({r for roles in ROLES.values() for r in roles})
for role in all_roles:
    n = client.count(COLLECTION_NAME, count_filter=models.Filter(must=[
        models.FieldCondition(key="access_roles", match=models.MatchAny(any=[role]))
    ])).count
    print(f"{role}: {n} chunks visible")