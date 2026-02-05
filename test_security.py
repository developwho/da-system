"""
Security sanity tests (API key + UUID validation).
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Suppress pydantic warnings from google-genai models during tests
warnings.filterwarnings(
    "ignore",
    message=r"Field name .* shadows an attribute in parent .*",
    category=UserWarning
)
warnings.filterwarnings(
    "ignore",
    message=r"Field .* has conflict with protected namespace .*",
    category=UserWarning
)

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


def test_api_key_required():
    settings.API_KEY = "test-key"
    client = TestClient(app)

    response = client.get("/api/v1/data")
    assert response.status_code == 401

    response = client.get("/api/v1/data", headers={"x-api-key": "test-key"})
    assert response.status_code == 200


def test_reports_invalid_uuid_rejected():
    settings.API_KEY = "test-key"
    client = TestClient(app)

    response = client.get("/api/v1/reports/not-a-uuid", headers={"x-api-key": "test-key"})
    assert response.status_code in {400, 422}


def test_research_path_validation_rejects_invalid_uuid():
    from app.utils.paths import resolve_research_path

    try:
        resolve_research_path("not-a-uuid", "papers.md")
        assert False, "Expected ValueError for invalid UUID"
    except ValueError:
        assert True


def test_llm_message_length_guard():
    from app.services.llm.base import LLMMessage
    from app.services.llm.openai_client import OpenAIClient

    settings.LLM_MAX_MESSAGE_LENGTH = 5
    client = OpenAIClient(api_key="test", model="gpt-4o")

    try:
        client.format_messages([LLMMessage(role="user", content="123456")])
        assert False, "Expected ValueError for long message"
    except ValueError:
        assert True
