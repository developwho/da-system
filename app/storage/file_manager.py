"""
파일 관리자
업로드된 파일을 저장하고 관리합니다.
"""
import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.config import settings
from app.utils.logger import get_logger
from app.utils.exceptions import InvalidFileFormatError

logger = get_logger(__name__)

# 업로드 디렉토리
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 메타데이터 디렉토리
METADATA_DIR = Path("data/metadata")
METADATA_DIR.mkdir(parents=True, exist_ok=True)


class FileManager:
    """파일 관리자"""

    @staticmethod
    def _normalize_file_id(file_id: str) -> str:
        """파일 ID 정규화 및 검증"""
        try:
            return str(uuid.UUID(str(file_id)))
        except ValueError:
            raise FileNotFoundError("Invalid file id")

    @staticmethod
    def save_upload(
        file_content: bytes,
        filename: str,
        file_id: str = None
    ) -> Dict[str, Any]:
        """
        업로드 파일 저장

        Args:
            file_content: 파일 내용
            filename: 원본 파일명
            file_id: 파일 ID (없으면 자동 생성)

        Returns:
            파일 정보
        """
        # 파일 ID 생성
        if file_id is None:
            file_id = str(uuid.uuid4())
        else:
            file_id = FileManager._normalize_file_id(file_id)

        # 파일 확장자 확인
        file_ext = Path(filename).suffix.lower()
        if file_ext not in {'.csv', '.xlsx', '.xls'}:
            raise InvalidFileFormatError(f"Unsupported file type: {file_ext}")

        # 저장 경로
        save_filename = f"{file_id}{file_ext}"
        save_path = UPLOAD_DIR / save_filename

        # 파일 저장
        with open(save_path, 'wb') as f:
            f.write(file_content)

        file_size = len(file_content)

        logger.info(
            "file_saved",
            file_id=file_id,
            filename=filename,
            size_bytes=file_size
        )

        return {
            "file_id": file_id,
            "filename": filename,
            "saved_path": str(save_path),
            "size_bytes": file_size,
            "extension": file_ext
        }

    @staticmethod
    def get_file_path(file_id: str) -> str:
        """
        파일 경로 조회

        Args:
            file_id: 파일 ID

        Returns:
            파일 경로

        Raises:
            FileNotFoundError: 파일이 없음
        """
        file_id = FileManager._normalize_file_id(file_id)

        # 가능한 확장자로 검색
        for ext in ['.csv', '.xlsx', '.xls']:
            file_path = UPLOAD_DIR / f"{file_id}{ext}"
            if file_path.exists():
                return str(file_path)

        raise FileNotFoundError(f"File not found: {file_id}")

    @staticmethod
    def save_metadata(
        file_id: str,
        original_filename: str,
        size_bytes: int,
        metadata: Dict[str, Any],
        validation: Dict[str, Any]
    ) -> None:
        """
        파일 메타데이터 저장

        Args:
            file_id: 파일 ID
            original_filename: 원본 파일명
            size_bytes: 파일 크기
            metadata: 데이터 메타데이터 (rows, columns 등)
            validation: 검증 정보
        """
        file_id = FileManager._normalize_file_id(file_id)
        metadata_path = METADATA_DIR / f"{file_id}.json"

        metadata_content = {
            "file_id": file_id,
            "original_filename": original_filename,
            "size_bytes": size_bytes,
            "metadata": metadata,
            "validation": validation,
            "uploaded_at": datetime.now().isoformat()
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_content, f, indent=2, ensure_ascii=False)

        logger.info("metadata_saved", file_id=file_id)

    @staticmethod
    def load_metadata(file_id: str) -> Optional[Dict[str, Any]]:
        """
        파일 메타데이터 로드

        Args:
            file_id: 파일 ID

        Returns:
            메타데이터 딕셔너리 또는 None (파일 없음)
        """
        try:
            file_id = FileManager._normalize_file_id(file_id)
            metadata_path = METADATA_DIR / f"{file_id}.json"

            if not metadata_path.exists():
                return None

            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("metadata_load_failed", file_id=file_id, error=str(e))
            return None

    @staticmethod
    def delete_file(file_id: str) -> bool:
        """
        파일 삭제 (데이터 파일 + 메타데이터 파일)

        Args:
            file_id: 파일 ID

        Returns:
            삭제 성공 여부
        """
        try:
            file_id = FileManager._normalize_file_id(file_id)

            # 데이터 파일 삭제
            file_path = FileManager.get_file_path(file_id)
            os.remove(file_path)

            # 메타데이터 파일 삭제
            metadata_path = METADATA_DIR / f"{file_id}.json"
            if metadata_path.exists():
                os.remove(metadata_path)

            logger.info("file_deleted", file_id=file_id)
            return True
        except FileNotFoundError:
            logger.warning("file_not_found_for_deletion", file_id=file_id)
            return False

    @staticmethod
    def list_files() -> list:
        """
        업로드된 파일 목록 (메타데이터 포함)

        Returns:
            파일 정보 리스트
        """
        files = []
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file() and file_path.suffix in {'.csv', '.xlsx', '.xls'}:
                file_id = file_path.stem

                # 메타데이터 로드 시도
                metadata_info = FileManager.load_metadata(file_id)

                if metadata_info:
                    # 메타데이터가 있으면 전체 정보 반환
                    files.append({
                        "file_id": file_id,
                        "filename": metadata_info.get("original_filename", file_path.name),
                        "size_bytes": metadata_info.get("size_bytes", file_path.stat().st_size),
                        "metadata": metadata_info.get("metadata", {}),
                        "validation": metadata_info.get("validation", {}),
                        "uploaded_at": metadata_info.get("uploaded_at")
                    })
                else:
                    # 메타데이터가 없으면 자동 재생성 시도 (레거시 파일)
                    metadata, validation = FileManager._regenerate_metadata(file_id, file_path)
                    files.append({
                        "file_id": file_id,
                        "filename": file_path.name,
                        "size_bytes": file_path.stat().st_size,
                        "metadata": metadata,
                        "validation": validation,
                        "uploaded_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
        return files

    @staticmethod
    def _regenerate_metadata(file_id: str, file_path: Path) -> tuple:
        """
        레거시 파일의 메타데이터를 자동 재생성

        Args:
            file_id: 파일 ID
            file_path: 파일 경로

        Returns:
            (metadata, validation) 튜플
        """
        try:
            from app.core.data_pipeline.loader import DataLoader
            from app.core.data_pipeline.validator import DataValidator

            df, metadata = DataLoader.load_file(str(file_path))
            validation = DataValidator.validate(df)

            # 다음 요청부터 재사용하도록 영속화
            FileManager.save_metadata(
                file_id=file_id,
                original_filename=file_path.name,
                size_bytes=file_path.stat().st_size,
                metadata=metadata,
                validation=validation
            )

            logger.info("metadata_regenerated", file_id=file_id)
            return metadata, validation

        except Exception as e:
            logger.warning("metadata_regeneration_failed", file_id=file_id, error=str(e))
            # 최소 기본값 반환
            return {
                "n_rows": 0,
                "n_columns": 0,
                "column_names": [],
                "dtypes": {},
                "memory_usage_bytes": 0,
                "size_bytes": file_path.stat().st_size
            }, {"is_valid": True}
