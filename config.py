import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    tavily_api_key: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    mysql_pool_size: int
    agent_max_turns: int
    max_history_items: int


settings = Settings(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    tavily_api_key=os.environ["TAVILY_API_KEY"],
    mysql_host=os.getenv("MYSQL_HOST", "localhost"),
    mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
    mysql_user=os.environ["MYSQL_USER"],
    mysql_password=os.environ["MYSQL_PASSWORD"],
    mysql_database=os.environ["MYSQL_DATABASE"],
    mysql_pool_size=int(os.getenv("MYSQL_POOL_SIZE", "5")),
    agent_max_turns=int(os.getenv("AGENT_MAX_TURNS", "15")),
    max_history_items=int(os.getenv("MAX_HISTORY_ITEMS", "40")),
)
