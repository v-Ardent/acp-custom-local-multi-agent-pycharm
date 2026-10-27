import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PYCHARM_MCP_URL = os.getenv(
    "PYCHARM_MCP_URL",
)

LLM = "gemma4:e4b"
MAX_ACTIVE_DISCOVERED = 6
MAX_ITERATIONS = 3
MAX_CONTEXT_SIZE = 131072

CHROMA_DB_PATH = Path(
    os.getenv("CHROMA_DB_PATH", "./memoire")
)