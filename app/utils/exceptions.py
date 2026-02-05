"""
커스텀 예외 클래스
"""


class DasystemException(Exception):
    """Base exception for DA System"""
    pass


class DataValidationError(DasystemException):
    """데이터 검증 실패"""
    pass


class InvalidFileFormatError(DataValidationError):
    """유효하지 않은 파일 형식"""
    pass


class MissingTargetVariableError(DataValidationError):
    """타겟 변수 누락"""
    pass


class InsufficientDataError(DataValidationError):
    """데이터 부족"""
    pass


class APIError(DasystemException):
    """외부 API 호출 실패"""
    pass


class LLMAPIError(APIError):
    """LLM API 오류"""
    pass


class HuggingFaceAPIError(APIError):
    """HuggingFace API 오류"""
    pass


class KaggleAPIError(APIError):
    """Kaggle API 오류"""
    pass


class DeepResearchAPIError(APIError):
    """DeepResearch API 오류"""
    pass


class ModelTrainingError(DasystemException):
    """모델 학습 실패"""
    pass


class FLAMLTrainingError(ModelTrainingError):
    """FLAML 학습 오류"""
    pass


class InsufficientMemoryError(ModelTrainingError):
    """메모리 부족"""
    pass


class ResearchFailedError(DasystemException):
    """선행연구 분석 실패"""
    pass


class ResourceLimitError(DasystemException):
    """리소스 한계 초과"""
    pass
