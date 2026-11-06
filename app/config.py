from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    VLM_MODE: Literal["mock", "vllm"] = "mock"
    VLLM_BASE_URL: str = "http://localhost:8001/v1"
    VLLM_API_KEY: str = "EMPTY"
    MODEL_ID: str = "Qwen/Qwen3-VL-8B-Instruct"
    VLM_TIMEOUT_SECONDS: float = 60.0
    VLM_MAX_TOKENS: int = 800
    MAX_CONCURRENCY: int = 4

    MAX_SIDE: int = 1600
    PDF_DPI: int = 150
    MAX_PDF_PAGES: int = 3
    JPEG_QUALITY: int = 90

    MAX_FILE_MB: int = 15
    MAX_FILES_PER_GROUP: int = 5
    STRICT: bool = False

    ALLOWED_EXT: set[str] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
        ".pdf",
    }


settings = Settings()
