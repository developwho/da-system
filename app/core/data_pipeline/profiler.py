"""
데이터 프로파일러
데이터셋의 통계적 특성을 분석합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataProfiler:
    """데이터 프로파일러"""

    @staticmethod
    def profile(df: pd.DataFrame) -> Dict[str, Any]:
        """
        데이터셋 프로파일 생성

        Args:
            df: DataFrame

        Returns:
            프로파일 딕셔너리
        """
        logger.info("profiling_data", rows=len(df), columns=len(df.columns))

        profile = {
            "overview": DataProfiler._get_overview(df),
            "variables": DataProfiler._analyze_variables(df),
            "correlations": DataProfiler._get_correlations(df),
            "missing_data": DataProfiler._analyze_missing_data(df)
        }

        logger.info("profiling_completed")
        return profile

    @staticmethod
    def _get_overview(df: pd.DataFrame) -> Dict[str, Any]:
        """데이터셋 개요"""
        total_cells = df.shape[0] * df.shape[1]
        total_rows = len(df)
        return {
            "n_variables": len(df.columns),
            "n_observations": total_rows,
            "missing_cells": int(df.isnull().sum().sum()),
            "missing_cells_pct": float((df.isnull().sum().sum() / total_cells) * 100) if total_cells else 0.0,
            "duplicate_rows": int(df.duplicated().sum()),
            "duplicate_rows_pct": float((df.duplicated().sum() / total_rows) * 100) if total_rows else 0.0,
            "memory_size_bytes": int(df.memory_usage(deep=True).sum()),
            "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": len(df.select_dtypes(include=['object', 'category']).columns),
            "datetime_columns": len(df.select_dtypes(include=['datetime64']).columns)
        }

    @staticmethod
    def _analyze_variables(df: pd.DataFrame) -> Dict[str, Dict]:
        """각 변수 분석"""
        variables = {}

        for col in df.columns:
            col_data = df[col]
            var_profile = {
                "type": str(col_data.dtype),
                "missing_count": int(col_data.isnull().sum()),
                "missing_pct": float((col_data.isnull().sum() / len(col_data)) * 100),
                "unique_count": int(col_data.nunique()),
                "unique_pct": float((col_data.nunique() / len(col_data)) * 100)
            }

            # 수치형 변수 통계
            if pd.api.types.is_numeric_dtype(col_data):
                var_profile["variable_type"] = "numeric"
                is_all_null = col_data.isnull().all()
                var_profile["statistics"] = {
                    "mean": float(col_data.mean()) if not is_all_null else None,
                    "std": float(col_data.std()) if not is_all_null else None,
                    "min": float(col_data.min()) if not is_all_null else None,
                    "25%": float(col_data.quantile(0.25)) if not is_all_null else None,
                    "50%": float(col_data.median()) if not is_all_null else None,
                    "75%": float(col_data.quantile(0.75)) if not is_all_null else None,
                    "max": float(col_data.max()) if not is_all_null else None,
                    "skewness": float(col_data.skew()) if not is_all_null else None,
                    "kurtosis": float(col_data.kurt()) if not is_all_null else None,
                    "zeros_count": int((col_data == 0).sum()),
                    "zeros_pct": float(((col_data == 0).sum() / len(col_data)) * 100)
                }

            # 범주형 변수 통계
            elif col_data.dtype.name in ['object', 'category']:
                var_profile["variable_type"] = "categorical"
                value_counts = col_data.value_counts()
                var_profile["top_values"] = value_counts.head(10).to_dict()
                var_profile["cardinality"] = len(value_counts)

                # 고빈도 vs 저빈도 카테고리
                if len(value_counts) > 0:
                    var_profile["most_frequent"] = {
                        "value": str(value_counts.index[0]),
                        "count": int(value_counts.iloc[0]),
                        "pct": float((value_counts.iloc[0] / len(col_data)) * 100)
                    }

            # DateTime 변수
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                var_profile["variable_type"] = "datetime"
                var_profile["statistics"] = {
                    "min": str(col_data.min()),
                    "max": str(col_data.max()),
                    "range_days": (col_data.max() - col_data.min()).days if not col_data.isnull().all() else None
                }

            variables[col] = var_profile

        return variables

    @staticmethod
    def _get_correlations(df: pd.DataFrame) -> Dict[str, Any]:
        """수치형 변수 간 상관관계"""
        numeric_df = df.select_dtypes(include=[np.number])

        if len(numeric_df.columns) < 2:
            return {"message": "상관관계 분석을 위한 수치형 변수가 부족합니다"}

        corr_matrix = numeric_df.corr()

        # 높은 상관관계 쌍 찾기 (절댓값 > 0.7)
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    high_corr_pairs.append({
                        "var1": corr_matrix.columns[i],
                        "var2": corr_matrix.columns[j],
                        "correlation": float(corr_val)
                    })

        return {
            "matrix": corr_matrix.to_dict(),
            "high_correlations": high_corr_pairs,
            "n_high_correlations": len(high_corr_pairs)
        }

    @staticmethod
    def _analyze_missing_data(df: pd.DataFrame) -> Dict[str, Any]:
        """결측치 분석"""
        missing_counts = df.isnull().sum()
        missing_pcts = (missing_counts / len(df)) * 100

        # 결측치가 있는 열만
        has_missing = missing_counts[missing_counts > 0]

        if len(has_missing) == 0:
            return {"message": "결측치가 없습니다"}

        missing_by_column = []
        for col in has_missing.index:
            missing_by_column.append({
                "column": col,
                "missing_count": int(missing_counts[col]),
                "missing_pct": float(missing_pcts[col])
            })

        # 결측치 비율로 정렬
        missing_by_column.sort(key=lambda x: x["missing_pct"], reverse=True)

        return {
            "total_missing_cells": int(df.isnull().sum().sum()),
            "columns_with_missing": len(has_missing),
            "missing_by_column": missing_by_column
        }

    @staticmethod
    def quick_summary(df: pd.DataFrame) -> str:
        """빠른 요약 (텍스트)"""
        total_cells = df.shape[0] * df.shape[1]
        missing_pct = (df.isnull().sum().sum() / total_cells * 100) if total_cells else 0.0
        summary_lines = [
            f"데이터셋: {len(df)} 행 × {len(df.columns)} 열",
            f"결측치: {df.isnull().sum().sum()} 개 ({missing_pct:.2f}%)",
            f"중복 행: {df.duplicated().sum()} 개",
            f"수치형 변수: {len(df.select_dtypes(include=[np.number]).columns)} 개",
            f"범주형 변수: {len(df.select_dtypes(include=['object', 'category']).columns)} 개",
            f"메모리 사용: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
        ]
        return "\n".join(summary_lines)
