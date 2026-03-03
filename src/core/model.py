from langchain_openai import ChatOpenAI#openai的接口
import os
from utils.env_utils import  OPEN_API_KEY
from langchain_openai import OpenAIEmbeddings

llm=ChatOpenAI(api_key=OPEN_API_KEY,
    model="Qwen/Qwen3-4B",
    temperature=0,
    base_url="https://api-inference.modelscope.cn/v1/",#具体指向某个模型，
   extra_body={"enable_thinking": False}
)

OCR_AGENT=ChatOpenAI(api_key=OPEN_API_KEY,
                     model="Qwen/Qwen3-Omni-30B-A3B-Instruct",
                     temperature=0,
                     base_url="https://api-inference.modelscope.cn/v1/" , # 具体指向某个模型，
                     extra_body={"enable_thinking": False}
                     )

from langchain_openai import OpenAIEmbeddings

embed_model = OpenAIEmbeddings(
    model="Qwen/Qwen3-Embedding-8B",
    api_key=OPEN_API_KEY,
    base_url="https://api-inference.modelscope.cn/v1/",
)






if __name__=="__main__":
    # ans=core.invoke("请给出什么是函数型数据的描述")
    # print(ans.content)
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that translates English to French."),
        ("human", "{input}")
    ])

    ai_msg = llm.invoke(prompt.format_messages(input="请你介绍一下函数型数据"))
