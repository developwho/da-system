"""
Data API 라우트
데이터 업로드 및 관리
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from typing import Dict, Any
from pydantic import UUID4

from app.core.data_pipeline.loader import DataLoader
from app.core.data_pipeline.validator import DataValidator
from app.core.data_pipeline.type_detector import TypeDetector
from app.core.data_pipeline.profiler import DataProfiler
from app.storage.file_manager import FileManager
from app.utils.logger import get_logger
from app.utils.exceptions import InvalidFileFormatError, DataValidationError
from app.api.deps import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = get_logger(__name__)


@router.post("/upload")
async def upload_data(file: UploadFile = File(...)):
    """
    데이터 파일 업로드

    지원 형식: CSV, Excel (.xlsx, .xls)
    최대 크기: 500MB
    """
    try:
        logger.info("file_upload_requested", filename=file.filename)

        # 파일 내용 읽기
        file_content = await file.read()

        # 크기 검증
        file_size = len(file_content)
        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes (max: {max_size})"
            )

        # 파일 저장
        file_info = FileManager.save_upload(file_content, file.filename)

        # 데이터 로드 및 메타데이터 추출
        df, metadata = DataLoader.load_file(file_info["saved_path"])

        # 기본 검증
        validation = DataValidator.validate(df)

        # 메타데이터 영속화
        FileManager.save_metadata(
            file_id=file_info["file_id"],
            original_filename=file.filename,
            size_bytes=file_size,
            metadata=metadata,
            validation=validation
        )

        # 미리보기 생성
        preview = DataLoader.get_preview(df, n=10)

        return {
            "file_id": file_info["file_id"],
            "filename": file.filename,
            "size_bytes": file_size,
            "metadata": metadata,
            "validation": validation,
            "preview": preview
        }

    except InvalidFileFormatError as e:
        logger.warning("invalid_file_format", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("file_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{file_id}")
async def get_data_info(file_id: UUID4):
    """데이터 정보 조회"""
    try:
        # 파일 경로 조회
        file_path = FileManager.get_file_path(str(file_id))

        # 데이터 로드
        df, metadata = DataLoader.load_file(file_path)

        # 검증
        validation = DataValidator.validate(df)

        return {
            "file_id": file_id,
            "metadata": metadata,
            "validation": validation
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    except Exception as e:
        logger.error("get_data_info_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}/profile")
async def get_data_profile(
    file_id: UUID4,
    target_column: str = Query(None, description="타겟 변수 (선택)")
):
    """
    데이터 프로파일 조회

    통계 분석, 상관관계, 결측치 분석 등 포함
    """
    try:
        # 파일 경로 조회
        file_path = FileManager.get_file_path(str(file_id))

        # 데이터 로드
        df, metadata = DataLoader.load_file(file_path)

        # 프로파일링
        profile = DataProfiler.profile(df)

        # 타겟 변수 분석 (있는 경우)
        target_analysis = None
        task_detection = None
        if target_column:
            try:
                target_analysis = DataValidator.check_target_variable(df, target_column)
                task_detection = TypeDetector.detect_task_type(df, target_column)
            except Exception as e:
                logger.warning("target_analysis_failed", error=str(e))

        return {
            "file_id": file_id,
            "profile": profile,
            "target_analysis": target_analysis,
            "task_detection": task_detection
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    except Exception as e:
        logger.error("profiling_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}/preview")
async def preview_data(
    file_id: UUID4,
    limit: int = Query(100, ge=1, le=1000, description="미리보기 행 수")
):
    """데이터 미리보기"""
    try:
        # 파일 경로 조회
        file_path = FileManager.get_file_path(str(file_id))

        # 데이터 로드
        df, metadata = DataLoader.load_file(file_path)

        # 미리보기 생성
        preview = DataLoader.get_preview(df, n=limit)

        return {
            "file_id": file_id,
            "preview": preview
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    except Exception as e:
        logger.error("preview_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_data(file_id: UUID4):
    """데이터 파일 삭제"""
    try:
        success = FileManager.delete_file(str(file_id))
        if success:
            return {"message": "File deleted", "file_id": file_id}
        else:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    except Exception as e:
        logger.error("delete_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_data_files():
    """업로드된 파일 목록"""
    try:
        files = FileManager.list_files()
        return {"files": files, "count": len(files)}
    except Exception as e:
        logger.error("list_files_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
