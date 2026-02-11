"""Reports API 라우트"""
from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import FileResponse, HTMLResponse
from typing import Dict, Any, List
from pathlib import Path
import os
import json
from pydantic import UUID4

from app.config import settings
from app.utils.logger import get_logger
from app.api.deps import require_api_key

router = APIRouter(tags=["reports"], dependencies=[Depends(require_api_key)])
logger = get_logger(__name__)


def _resolve_report_path(session_id: UUID4, filename: str) -> Path:
    base_dir = (Path(settings.OUTPUTS_DIR) / "reports").resolve()
    report_path = (base_dir / str(session_id) / filename).resolve()
    try:
        report_path.relative_to(base_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id")
    return report_path


@router.get("/{session_id}")
async def get_markdown_report(session_id: UUID4) -> Dict[str, Any]:
    """
    Markdown 리포트 조회

    Args:
        session_id: 세션 ID

    Returns:
        리포트 내용 및 메타데이터
    """
    try:
        report_path = _resolve_report_path(session_id, "report.md")

        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        # 리포트 읽기
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 메타데이터 읽기
        metadata_path = report_path.parent / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        return {
            "session_id": str(session_id),
            "content": content,
            "format": "markdown",
            "metadata": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get markdown report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/html")
async def get_html_report(session_id: UUID4) -> HTMLResponse:
    """
    HTML 리포트 조회

    Args:
        session_id: 세션 ID

    Returns:
        HTML 리포트
    """
    try:
        report_path = _resolve_report_path(session_id, "report.html")

        if not report_path.exists():
            raise HTTPException(status_code=404, detail="HTML report not found")

        # HTML 읽기
        with open(report_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HTML report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/download")
async def download_artifacts(session_id: UUID4) -> FileResponse:
    """
    Artifacts ZIP 다운로드

    Args:
        session_id: 세션 ID

    Returns:
        ZIP 파일
    """
    try:
        zip_path = _resolve_report_path(session_id, "artifacts.zip")

        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="Artifacts not found")

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"analysis_artifacts_{session_id}.zip"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download artifacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/metadata")
async def get_report_metadata(session_id: UUID4) -> Dict[str, Any]:
    """
    리포트 메타데이터 조회

    Args:
        session_id: 세션 ID

    Returns:
        메타데이터
    """
    try:
        metadata_path = _resolve_report_path(session_id, "metadata.json")

        if not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Metadata not found")

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_reports() -> List[Dict[str, Any]]:
    """
    모든 리포트 목록 조회

    Returns:
        리포트 목록
    """
    try:
        reports_dir = Path(settings.OUTPUTS_DIR) / "reports"

        if not reports_dir.exists():
            return []

        reports = []
        for session_dir in reports_dir.iterdir():
            if session_dir.is_dir():
                metadata_path = session_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        reports.append({
                            "session_id": session_dir.name,
                            "timestamp": metadata.get("timestamp"),
                            "problem_type": metadata.get("problem_type"),
                            "model": metadata.get("model"),
                        })

        # 최신순 정렬
        reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return reports

    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_report(session_id: UUID4) -> Dict[str, str]:
    """
    리포트 삭제

    Args:
        session_id: 세션 ID

    Returns:
        성공 메시지
    """
    try:
        report_dir = _resolve_report_path(session_id, "report.md").parent

        if not report_dir.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        # 디렉토리 삭제
        import shutil
        shutil.rmtree(report_dir)

        logger.info(f"Report deleted: {session_id}")

        return {"message": "Report deleted successfully", "session_id": str(session_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/files")
async def list_report_files(session_id: UUID4) -> Dict[str, Any]:
    """
    리포트 관련 파일 목록 조회

    Args:
        session_id: 세션 ID

    Returns:
        파일 목록
    """
    try:
        report_dir = _resolve_report_path(session_id, "report.md").parent

        if not report_dir.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        files = {
            "markdown": None,
            "html": None,
            "artifacts": None,
            "metadata": None,
        }

        # 파일 확인
        if (report_dir / "report.md").exists():
            files["markdown"] = str(report_dir / "report.md")

        if (report_dir / "report.html").exists():
            files["html"] = str(report_dir / "report.html")

        if (report_dir / "artifacts.zip").exists():
            files["artifacts"] = str(report_dir / "artifacts.zip")

        if (report_dir / "metadata.json").exists():
            files["metadata"] = str(report_dir / "metadata.json")

        return {"session_id": str(session_id), "files": files}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
