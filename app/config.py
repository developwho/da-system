"""
애플리케이션 설정 모듈
환경 변수를 로드하고 검증합니다.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    SECRET_KEY: str
    API_KEY: Optional[str] = None
    PROJECT_NAME: str = "DA System"
    VERSION: str = "0.1.0"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM APIs
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5-mini-2025-08-07"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_MESSAGE_LENGTH: int = 8000
    LLM_MAX_TOKENS: int = 4096
    LLM_MAX_RETRIES: int = 2
    CHAT_LLM_PROVIDER: str = "gemini"  # 채팅용 기본 LLM (gemini, openai, anthropic)

    # External APIs
    HUGGINGFACE_TOKEN: Optional[str] = None
    KAGGLE_USERNAME: Optional[str] = None
    KAGGLE_KEY: Optional[str] = None

    # MLflow
    MLFLOW_TRACKING_URI: str = "file:./mlruns"

    # CORS (쉼표로 구분된 문자열로 받음)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://localhost:8080"

    @property
    def allowed_origins_list(self) -> List[str]:
        """CORS allowed origins를 리스트로 반환"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Resource Limits
    MAX_UPLOAD_SIZE_MB: int = 500
    MAX_CONCURRENT_TASKS: int = 5
    FLAML_DEFAULT_TIME_BUDGET: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    # Directories
    OUTPUTS_DIR: str = "outputs"
    DATA_DIR: str = "data"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_api_keys(self) -> dict:
        """API 키 유효성 검증"""
        validation = {
            "openai": bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.startswith("sk-")),
            "anthropic": bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY.startswith("sk-ant-")),
            "google": bool(self.GOOGLE_API_KEY),
            "huggingface": bool(self.HUGGINGFACE_TOKEN),
            "kaggle": bool(self.KAGGLE_USERNAME and self.KAGGLE_KEY)
        }
        return validation

    @property
    def max_upload_size_bytes(self) -> int:
        """최대 업로드 크기 (바이트)"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# 전역 설정 인스턴스
settings = Settings()
