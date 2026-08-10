import os
from dotenv import load_dotenv
load_dotenv()

DEBUG_PORT=int(os.getenv("DEBUG_PORT","9222"))
CLAUDE_URL=os.getenv("CLAUDE_URL","https://claude.ai/new")
MAX_RETRIES=int(os.getenv("MAX_RETRIES","3"))
RESPONSE_TIMEOUT_MS=int(os.getenv("RESPONSE_TIMEOUT_MS","120000"))
BETWEEN_ROWS_MS=int(os.getenv("BETWEEN_ROWS_MS","1500"))
INPUT_DIR="input"
OUTPUT_DIR="output"
