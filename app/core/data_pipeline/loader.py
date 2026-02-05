"""
데이터 로더
CSV, Excel 파일을 로드하고 메타데이터를 추출합니다.
"""
import json

import numpy as np
import pandas as pd
import dask.dataframe as dd
from pathlib import Path
from typing import Tuple, Dict, Any
import uuid
from datetime import datetime

from app.utils.logger import get_logger
from app.utils.exceptions import InvalidFileFormatError, InsufficientDataError

logger = get_logger(__name__)

# 지원하는 파일 형식
SUPPORTED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
LARGE_FILE_THRESHOLD = 500 * 1024 * 1024  # 500MB


class DataLoader:
    """데이터 로더 클래스"""

    @staticmethod
    def load_file(file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        파일 로드 및 메타데이터 추출

        Args:
            file_path: 파일 경로
            **kwargs: 추가 로드 옵션

        Returns:
            (DataFrame, metadata)

        Raises:
            InvalidFileFormatError: 지원하지 않는 파일 형식
            InsufficientDataError: 데이터 부족
        """
        path = Path(file_path)

        # 파일 형식 검증
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise InvalidFileFormatError(f"Unsupported file format: {path.suffix}")

        # 파일 크기 확인
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        file_size = path.stat().st_size
        logger.info("loading_file", filename=path.name, size_bytes=file_size)

        # 파일 로드
        if file_size > LARGE_FILE_THRESHOLD:
            # Dask로 대용량 파일 처리
            logger.info("using_dask_for_large_file", size_mb=file_size / 1024 / 1024)
            df = DataLoader._load_with_dask(file_path, **kwargs)
        else:
            # Pandas로 일반 파일 처리
            df = DataLoader._load_with_pandas(file_path, **kwargs)

        # 메타데이터 추출
        metadata = DataLoader._extract_metadata(df, path, file_size)

        # 데이터 검증
        if len(df) < 10:
            raise InsufficientDataError(f"Insufficient data: only {len(df)} rows")

        logger.info("file_loaded_successfully",
                    rows=len(df),
                    columns=len(df.columns),
                    memory_mb=df.memory_usage(deep=True).sum() / 1024 / 1024)

        return df, metadata

    @staticmethod
    def _load_with_pandas(file_path: str, **kwargs) -> pd.DataFrame:
        """Pandas로 파일 로드"""
        path = Path(file_path)

        if path.suffix.lower() == '.csv':
            # CSV 로드 (인코딩 자동 감지)
            try:
                df = pd.read_csv(file_path, **kwargs)
            except UnicodeDecodeError:
                # CP949 인코딩 시도 (한국어 파일)
                logger.warning("utf8_decode_failed_trying_cp949")
                df = pd.read_csv(file_path, encoding='cp949', **kwargs)
        else:
            # Excel 로드
            df = pd.read_excel(file_path, **kwargs)

        return df

    @staticmethod
    def _load_with_dask(file_path: str, **kwargs) -> pd.DataFrame:
        """Dask로 대용량 파일 로드"""
        path = Path(file_path)

        if path.suffix.lower() == '.csv':
            ddf = dd.read_csv(file_path, **kwargs)
            # 샘플링 또는 전체 로드 (메모리 허용 시)
            # 현재는 전체 로드 (향후 개선 가능)
            df = ddf.compute()
        else:
            # Dask는 Excel을 직접 지원하지 않으므로 Pandas 사용
            logger.warning("dask_excel_not_supported_using_pandas")
            df = pd.read_excel(file_path, **kwargs)

        return df

    @staticmethod
    def _extract_metadata(df: pd.DataFrame, path: Path, file_size: int) -> Dict[str, Any]:
        """메타데이터 추출"""
        file_id = str(uuid.uuid4())

        metadata = {
            "file_id": file_id,
            "filename": path.name,
            "size_bytes": file_size,
            "n_rows": len(df),
            "n_columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
            "upload_time": datetime.now().isoformat(),
            "has_missing_values": bool(df.isnull().any().any()),
            "total_missing_values": int(df.isnull().sum().sum())
        }

        return metadata

    @staticmethod
    def get_sample(df: pd.DataFrame, n: int = 100) -> pd.DataFrame:
        """데이터 샘플 추출"""
        if len(df) <= n:
            return df
        return df.sample(n=n, random_state=42)

    @staticmethod
    def get_preview(df: pd.DataFrame, n: int = 100) -> Dict[str, Any]:
        """데이터 미리보기 생성"""
        # Use to_json + json.loads to safely convert numpy types to native Python
        head_records = json.loads(df.head(n).to_json(orient='records'))
        preview = {
            "head": head_records,
            "shape": list(df.shape),
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        return preview
