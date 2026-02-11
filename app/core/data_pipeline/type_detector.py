"""
문제 유형 자동 감지
데이터셋을 분석하여 ML 태스크 유형을 자동으로 감지합니다.
"""
import pandas as pd
from typing import Literal, Dict, Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

TaskType = Literal[
    "binary_classification",
    "multiclass_classification",
    "regression",
    "timeseries"
]


class TypeDetector:
    """문제 유형 감지기"""

    @staticmethod
    def detect(df: pd.DataFrame) -> Dict[str, Any]:
        """
        타겟 변수를 자동 추정하여 문제 유형 감지

        Returns:
            {
                "problem_type": str,
                "confidence": float,
                "reasoning": str,
                "details": dict,
                "recommended_target": str,
                "is_balanced": bool,
                "imbalance_ratio": float,
                "class_distribution": dict
            }
        """
        target_column = TypeDetector._infer_target_column(df)
        detection = TypeDetector.detect_task_type(df, target_column)
        task_type = detection.get("task_type")
        problem_type = "time_series" if task_type == "timeseries" else task_type

        details = detection.get("details", {})

        result = {
            "problem_type": problem_type,
            "confidence": detection.get("confidence", 0.0),
            "reasoning": detection.get("reasoning", ""),
            "details": details,
            "recommended_target": target_column,
        }

        # 분류 문제의 경우 불균형 정보 추가
        if target_column and target_column in df.columns:
            target = df[target_column]
            is_balanced = details.get("is_balanced", True)
            result["is_balanced"] = is_balanced

            class_dist = details.get("class_distribution", {})
            result["class_distribution"] = class_dist

            if class_dist:
                max_count = max(class_dist.values())
                min_count = min(class_dist.values()) if class_dist else 1
                result["imbalance_ratio"] = round(max_count / min_count, 2) if min_count > 0 else float("inf")
            else:
                result["imbalance_ratio"] = 1.0
        else:
            result["is_balanced"] = True
            result["imbalance_ratio"] = 1.0
            result["class_distribution"] = {}

        return result

    @staticmethod
    def detect_task_type(
        df: pd.DataFrame,
        target_column: str
    ) -> Dict[str, Any]:
        """
        ML 태스크 유형 자동 감지

        Args:
            df: DataFrame
            target_column: 타겟 변수명

        Returns:
            {
                "task_type": str,
                "confidence": float,
                "reasoning": str,
                "details": dict
            }
        """
        if not target_column or target_column not in df.columns:
            return {
                "task_type": "unknown",
                "confidence": 0.0,
                "reasoning": "타겟 변수를 찾을 수 없습니다",
                "details": {"available_columns": df.columns.tolist()}
            }

        target = df[target_column]

        # 1. 시계열 데이터 감지
        if TypeDetector._is_timeseries(df):
            return {
                "task_type": "timeseries",
                "confidence": 0.9,
                "reasoning": "데이터에 시간 인덱스가 있고 순차적 패턴이 감지됨",
                "details": {
                    "has_datetime_index": isinstance(df.index, pd.DatetimeIndex),
                    "has_datetime_column": TypeDetector._has_datetime_column(df)
                }
            }

        # 2. 분류 vs 회귀 판별
        if TypeDetector._is_classification(target):
            # 이진 분류 vs 다중 분류
            n_unique = target.nunique()

            if n_unique == 2:
                task_type = "binary_classification"
                reasoning = f"타겟 변수가 2개의 고유값을 가집니다: {target.unique().tolist()}"
            else:
                task_type = "multiclass_classification"
                reasoning = f"타겟 변수가 {n_unique}개의 클래스를 가집니다"

            return {
                "task_type": task_type,
                "confidence": 0.95,
                "reasoning": reasoning,
                "details": {
                    "n_classes": n_unique,
                    "class_distribution": target.value_counts().to_dict(),
                    "is_balanced": TypeDetector._is_balanced(target)
                }
            }

        else:
            # 회귀
            return {
                "task_type": "regression",
                "confidence": 0.9,
                "reasoning": f"타겟 변수가 연속형 수치입니다 (고유값: {target.nunique()}개)",
                "details": {
                    "n_unique": target.nunique(),
                    "target_range": {
                        "min": float(target.min()),
                        "max": float(target.max()),
                        "mean": float(target.mean()),
                        "std": float(target.std())
                    }
                }
            }

    @staticmethod
    def _is_timeseries(df: pd.DataFrame) -> bool:
        """시계열 데이터 여부 판별"""
        # DateTime 인덱스 확인
        if isinstance(df.index, pd.DatetimeIndex):
            return True

        # DateTime 타입 열이 있고 정렬되어 있는지 확인
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        if len(datetime_cols) > 0:
            # 첫 번째 datetime 열로 정렬 확인
            first_dt_col = datetime_cols[0]
            series = df[first_dt_col].dropna()
            if len(series) == 0:
                return False
            is_sorted = series.is_monotonic_increasing or series.is_monotonic_decreasing
            return is_sorted

        return False

    @staticmethod
    def _has_datetime_column(df: pd.DataFrame) -> bool:
        """DataFrame에 datetime 타입 열이 있는지 확인"""
        return len(df.select_dtypes(include=['datetime64']).columns) > 0

    @staticmethod
    def _infer_target_column(df: pd.DataFrame) -> str:
        """타겟 변수 추정"""
        preferred_names = ["target", "label", "y", "outcome"]
        for name in preferred_names:
            if name in df.columns:
                return name
        return df.columns[-1] if len(df.columns) > 0 else ""

    @staticmethod
    def _is_classification(target: pd.Series) -> bool:
        """분류 문제 여부 판별"""
        # 1. 명시적 범주형 타입
        if target.dtype.name in ['object', 'category', 'bool']:
            return True

        # 2. 수치형이지만 분류로 판단되는 경우
        if pd.api.types.is_numeric_dtype(target):
            n_unique = target.nunique()
            n_samples = len(target)

            # 고유값이 매우 적으면 분류
            if n_unique < 10:
                return True

            # 고유값 비율이 5% 미만이면 분류
            if (n_unique / n_samples) < 0.05:
                return True

            # 모두 정수이고 연속적이지 않으면 분류
            if target.dtype in ['int64', 'int32']:
                if not TypeDetector._is_continuous_integers(target):
                    return True

        return False

    @staticmethod
    def _is_continuous_integers(target: pd.Series) -> bool:
        """정수가 연속적인지 확인 (집값, 급여 등 넓은 범위의 수치도 연속형으로 판정)"""
        unique_vals = sorted(target.dropna().unique())
        n_unique = len(unique_vals)
        if n_unique < 2:
            return True

        value_range = unique_vals[-1] - unique_vals[0]

        # 고유값 20+개 AND 범위 100+ → 연속형 (집값, 급여 등)
        if n_unique > 20 and value_range > 100:
            return True

        # 기존: 값 간 차이가 대부분 1이면 연속적 (인코딩 라벨 감지용)
        diffs = [unique_vals[i+1] - unique_vals[i] for i in range(n_unique - 1)]
        avg_diff = sum(diffs) / len(diffs)
        return avg_diff <= 2

    @staticmethod
    def _is_balanced(target: pd.Series) -> bool:
        """클래스 균형 여부 확인"""
        value_counts = target.value_counts()
        max_count = value_counts.max()
        min_count = value_counts.min()

        # 최대와 최소의 비율이 3배 이하면 균형
        return (max_count / min_count) <= 3

    @staticmethod
    def suggest_metrics(task_type: TaskType) -> list:
        """태스크 유형별 추천 메트릭"""
        metrics_map = {
            "binary_classification": ["roc_auc", "precision", "recall", "f1", "accuracy"],
            "multiclass_classification": ["accuracy", "f1_weighted", "precision_weighted"],
            "regression": ["rmse", "mae", "r2", "mape"],
            "timeseries": ["rmse", "mae", "mape", "smape"],
            "time_series": ["rmse", "mae", "mape", "smape"]
        }
        return metrics_map.get(task_type, ["accuracy"])
