"""
데이터 검증
데이터 무결성 및 품질을 검증합니다.
"""
import pandas as pd
from typing import Dict, List, Any

from app.utils.logger import get_logger
from app.utils.exceptions import DataValidationError, MissingTargetVariableError

logger = get_logger(__name__)


class DataValidator:
    """데이터 검증기"""

    @staticmethod
    def validate(df: pd.DataFrame, target_column: str = None) -> Dict[str, Any]:
        """
        데이터 검증 수행

        Args:
            df: DataFrame
            target_column: 타겟 변수 (선택적)

        Returns:
            검증 결과 딕셔너리
        """
        errors = []
        warnings = []
        suggestions = []

        # 1. 최소 행/열 검증
        if len(df) < 10:
            errors.append("데이터가 너무 적습니다 (최소 10행 필요)")

        if len(df.columns) < 2:
            errors.append("열이 너무 적습니다 (최소 2열 필요)")

        # 2. 타겟 변수 검증
        if target_column:
            if target_column not in df.columns:
                errors.append(f"타겟 변수 '{target_column}'를 찾을 수 없습니다")
            else:
                # 타겟 변수 결측치 확인
                target_missing = df[target_column].isnull().sum()
                if target_missing > 0:
                    warnings.append(
                        f"타겟 변수에 {target_missing}개의 결측치가 있습니다"
                    )

        # 3. 중복 행 검증
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            warnings.append(f"{duplicates}개의 중복 행이 있습니다")
            suggestions.append("중복 행 제거를 고려하세요")

        # 4. 결측치 검증
        total_missing = df.isnull().sum().sum()
        if total_missing > 0:
            missing_pct = (total_missing / (df.shape[0] * df.shape[1])) * 100
            warnings.append(
                f"전체 데이터의 {missing_pct:.2f}%가 결측치입니다"
            )

            # 결측치가 많은 열 식별
            high_missing_cols = df.isnull().sum()
            high_missing_cols = high_missing_cols[high_missing_cols / len(df) > 0.5]
            if len(high_missing_cols) > 0:
                suggestions.append(
                    f"결측치가 50% 이상인 열: {high_missing_cols.index.tolist()}"
                )

        # 5. 데이터 타입 일관성
        for col in df.columns:
            # 숫자로 보이지만 문자열인 열 감지
            if df[col].dtype == 'object':
                try:
                    pd.to_numeric(df[col], errors='coerce')
                    suggestions.append(
                        f"'{col}' 열이 숫자로 변환 가능할 수 있습니다"
                    )
                except (ValueError, TypeError) as exc:
                    logger.debug("numeric_conversion_failed", column=col, error=str(exc))

        # 6. 상수 열 검증 (값이 하나만 있는 열)
        constant_cols = [col for col in df.columns if df[col].nunique() == 1]
        if constant_cols:
            warnings.append(f"상수 열 발견: {constant_cols}")
            suggestions.append("상수 열은 모델링에 도움이 되지 않습니다")

        # 검증 결과
        is_valid = len(errors) == 0

        result = {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "summary": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "missing_values": int(total_missing),
                "duplicate_rows": int(duplicates),
                "constant_columns": len(constant_cols)
            }
        }

        logger.info("data_validation_completed",
                    is_valid=is_valid,
                    errors_count=len(errors),
                    warnings_count=len(warnings))

        return result

    @staticmethod
    def check_target_variable(df: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        """타겟 변수 상세 검증"""
        if target_column not in df.columns:
            raise MissingTargetVariableError(
                f"Target variable '{target_column}' not found"
            )

        target = df[target_column]

        analysis = {
            "name": target_column,
            "dtype": str(target.dtype),
            "nunique": int(target.nunique()),
            "missing_count": int(target.isnull().sum()),
            "missing_pct": float((target.isnull().sum() / len(target)) * 100)
        }

        # 수치형 타겟
        if pd.api.types.is_numeric_dtype(target):
            analysis["type"] = "numeric"
            analysis["stats"] = {
                "mean": float(target.mean()),
                "std": float(target.std()),
                "min": float(target.min()),
                "max": float(target.max()),
                "median": float(target.median())
            }

        # 범주형 타겟
        else:
            analysis["type"] = "categorical"
            value_counts = target.value_counts()
            analysis["value_counts"] = value_counts.to_dict()
            analysis["top_values"] = value_counts.head(10).to_dict()

        return analysis
