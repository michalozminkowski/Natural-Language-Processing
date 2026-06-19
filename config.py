import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")


OLLAMA_EXTRACT_MODEL = os.getenv("OLLAMA_EXTRACT_MODEL", "llama3.2")


OLLAMA_RESPONSE_MODEL = os.getenv("OLLAMA_RESPONSE_MODEL", "llama3.2")


OLLAMA_METADATA_MODEL = os.getenv("OLLAMA_METADATA_MODEL", "llama3.2")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)