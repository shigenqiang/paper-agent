import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPEN_API_KEY = os.getenv('OPEN_API_KEY')

MILVUS_URI = os.getenv('MILVUS_URI')
COLLECTION_NAME =os.getenv('COLLECTION_NAME')

password=os.getenv('password')

user=os.getenv('user')

LANGCHAIN_TRACING_V2 =os.getenv('LANGCHAIN_TRACING_V2')
LANGCHAIN_API_KEY=os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT =os.getenv('LANGCHAIN_PROJECT')

