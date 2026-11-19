from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (Northwind-Bank/), so .env is found no matter which folder you run from
BASE_DIR = Path(__file__).resolve().parent.parent

'''
`lru_cache` remembers what a function returned, so if you call the function again with the same arguments, Python hands back the saved result instead of running it again.

In a config file, it's normally used to make sure the settings are loaded only once:

**What it does here:**
- **On the first call** to `get_settings()`, the `.env` file is read, each value is checked against its type, and the resulting `Settings` object is saved.
- **On every later call**, from `db.py`, `vector.py`, `main.py` or anywhere else, you get that **same saved object** straight away. The file isn't read again.

**Why it matters:**
1. **Speed:** reading and validating `.env` on every request would waste time.
2. **Consistency:** every module sees the same settings object.
3. **Testing:** in tests you can call `get_settings.cache_clear()` to reload the settings, or swap in fake settings with FastAPI's `app.dependency_overrides[get_settings]`.

Without `lru_cache`, each `get_settings()` call would create a new `Settings()` and read `.env` from disk again.

'''

class Settings(BaseSettings): #inheriting the pydantic base settings
    model_config=SettingsConfigDict(env_file=BASE_DIR / '.env',extra='ignore')

    # AWS
    aws_region:str='us-east-1'
    aws_access_key_id:str=''
    aws_secret_access_key:str=''
    s3_bucket:str=''
    max_upload_bytes:int=10485760

    # Pinecone
    pinecone_api_key:str=''
    pinecone_index:str=''
    pinecone_cloud:str='aws'
    pinecone_region:str='us-east-1'
    pinecone_ready_timeout:int=180

    # PostgreSQL on render
    database_url:str=''
    database_password:str=''
    database_name:str=''
    database_username:str=''

    #
    db_instance_identifier:str=''
    db_password:str=''
    initial_db:str= ''
    rds_db_url:str=''

    # LangSmith
    langsmith_tracing:bool= False
    langsmith_api_key:str=''
    langsmith_project:str='northwind'

    # App
    min_relevance:float=0.25
    hitl_enabled:bool=True
    memory_turns:int=6

    # Amazon models from Bedrock
    BEDROCK_EMBED_MODEL: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_CHAT_MODEL: str = "us.amazon.nova-2-lite-v1:0"  # inference profile ID (required for Nova)
    EMBED_DIMENSION: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
