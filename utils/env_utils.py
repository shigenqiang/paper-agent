import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPEN_API_KEY = os.getenv('OPEN_API_KEY')

MILVUS_URI = 'https://in03-169d749fd79c27c.serverless.aws-eu-central-1.cloud.zilliz.com'

COLLECTION_NAME = 'paper_Data'

password="Ul9-wTe~Xo7vF]Q3"

user="db_169d749fd79c27c"

LANGCHAIN_TRACING_V2 =os.getenv('LANGCHAIN_TRACING_V2')
LANGCHAIN_API_KEY=os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT =os.getenv('LANGCHAIN_PROJECT')

