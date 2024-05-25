from langchain_openai import ChatOpenAI
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_chat_model():
    # chat_model = ChatOpenAI(
    #     temperature=0.4, 
    #     # base_url="https://api.groq.com/openai/v1/",
    #     model_name="gpt-4o",
    #     # api_key=GROQ_API_KEY
    # )

    chat_model = ChatOpenAI(
        temperature=0.4, 
        base_url="https://api.groq.com/openai/v1/",
        model_name="llama3-70b-8192",
        api_key=GROQ_API_KEY
    )

    return chat_model

def get_tools_model():
    tools_model = ChatOpenAI(
        temperature=0.0, 
        # base_url="https://api.groq.com/openai/v1/",
        model_name="gpt-4o",
        # api_key=GROQ_API_KEY
    )

    return tools_model

let_user_know_model = ChatOpenAI(
    temperature=0.4, 
    base_url="https://api.groq.com/openai/v1/",
    model_name="llama3-8b-8192",
    api_key=GROQ_API_KEY
)
