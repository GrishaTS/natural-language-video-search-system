from functools import lru_cache

from langchain_openai import ChatOpenAI
from src.core.config import settings


@lru_cache(maxsize=1)
def get_langchain_llm() -> ChatOpenAI:
    """Return a cached LangChain ChatOpenAI client pointed at the AI service proxy."""

    return ChatOpenAI(
        model="llm",
        base_url=settings.AI_URL,
        api_key=settings.SERVICE_TOKEN,
        temperature=0.1,
        streaming=True,
    )
