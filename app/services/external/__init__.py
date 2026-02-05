"""외부 API 서비스 패키지"""
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .huggingface import HuggingFaceClient
    from .kaggle import KaggleClient
    from .deep_research import DeepResearchClient

__all__ = ["HuggingFaceClient", "KaggleClient", "DeepResearchClient"]


def __getattr__(name: str):
    if name == "HuggingFaceClient":
        return import_module(".huggingface", __name__).HuggingFaceClient
    if name == "KaggleClient":
        return import_module(".kaggle", __name__).KaggleClient
    if name == "DeepResearchClient":
        return import_module(".deep_research", __name__).DeepResearchClient
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__():
    return sorted(list(__all__))
