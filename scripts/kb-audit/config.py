import os
from dotenv import load_dotenv

def load_config(script_dir: str) -> dict:
    """Load config from .env file in script_dir, with env var overrides."""
    load_dotenv(os.path.join(script_dir, ".env"))
    return {
        "openai_api_key": os.environ["OPENAI_API_KEY"],
        "similarity_threshold": float(os.getenv("KB_AUDIT_SIMILARITY_THRESHOLD", "0.85")),
        "contradiction_range_low": float(os.getenv("KB_AUDIT_CONTRADICTION_RANGE_LOW", "0.75")),
        "contradiction_range_high": float(os.getenv("KB_AUDIT_CONTRADICTION_RANGE_HIGH", "0.85")),
        "thin_file_words": int(os.getenv("KB_AUDIT_THIN_FILE_WORDS", "100")),
        "long_file_words": int(os.getenv("KB_AUDIT_LONG_FILE_WORDS", "3000")),
        "wall_of_text_words": int(os.getenv("KB_AUDIT_WALL_OF_TEXT_WORDS", "500")),
        "stale_months": int(os.getenv("KB_AUDIT_STALE_MONTHS", "12")),
        "model": os.getenv("KB_AUDIT_MODEL", "gpt-4o"),
        "embedding_model": os.getenv("KB_AUDIT_EMBEDDING_MODEL", "text-embedding-3-small"),
    }
