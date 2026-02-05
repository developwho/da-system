"""
Analysis API 라우트
모델 학습 및 분석 작업 관리
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import asyncio

from app.tasks.modeling_tasks import train_automl_model, evaluate_model
from app.utils.logger import get_logger
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
from app.api.deps import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = get_logger(__name__)


class TrainingRequest(BaseModel):
    """모델 학습 요청"""
    file_id: str
    target_column: str
    config: Optional[Dict[str, Any]] = None


class EvaluationRequest(BaseModel):
    """모델 평가 요청"""
    model_id: str
    test_file_id: str


@router.post("/train")
async def start_training(request: TrainingRequest):
    """
    AutoML 모델 학습 시작

    비동기 Celery 작업으로 실행되며, task_id를 반환합니다.
    작업 상태는 /tasks/{task_id} 엔드포인트로 조회할 수 있습니다.
    """
    try:
        logger.info(
            "training_request_received",
            file_id=request.file_id,
            target_column=request.target_column
        )

        # Celery 작업 시작
        task = train_automl_model.apply_async(
            kwargs={
                "file_id": request.file_id,
                "target_column": request.target_column,
                "config": request.config
            }
        )

        logger.info("training_task_started", task_id=task.id)

        return {
            "status": "started",
            "task_id": task.id,
            "message": "Training started. Use /tasks/{task_id} to check status."
        }

    except Exception as e:
        logger.error("training_start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


@router.post("/evaluate")
async def start_evaluation(request: EvaluationRequest):
    """
    모델 평가 시작

    테스트 데이터로 모델을 평가합니다.
    """
    try:
        logger.info(
            "evaluation_request_received",
            model_id=request.model_id,
            test_file_id=request.test_file_id
        )

        # Celery 작업 시작
        task = evaluate_model.apply_async(
            kwargs={
                "model_id": request.model_id,
                "test_file_id": request.test_file_id
            }
        )

        logger.info("evaluation_task_started", task_id=task.id)

        return {
            "status": "started",
            "task_id": task.id,
            "message": "Evaluation started. Use /tasks/{task_id} to check status."
        }

    except Exception as e:
        logger.error("evaluation_start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start evaluation: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    작업 상태 조회

    Returns:
        - status: PENDING, LOADING, PREPROCESSING, TRAINING, EVALUATING, COMPLETED, FAILURE
        - progress: 0-100
        - message: 현재 단계 메시지
        - result: 완료 시 결과 (COMPLETED 상태)
        - error: 실패 시 에러 정보 (FAILURE 상태)
    """
    try:
        task = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": task.status,
        }

        if task.status == "PENDING":
            response["progress"] = 0
            response["message"] = "Task is waiting to be executed"

        elif task.status in ["LOADING", "PREPROCESSING", "TRAINING", "EVALUATING"]:
            # 진행 중인 작업
            if task.info:
                response["progress"] = task.info.get("progress", 0)
                response["message"] = task.info.get("message", "Processing...")
            else:
                response["progress"] = 0
                response["message"] = "Processing..."

        elif task.status == "SUCCESS":
            # 완료된 작업
            response["status"] = "COMPLETED"
            response["progress"] = 100
            response["message"] = "Task completed successfully"
            response["result"] = task.result

        elif task.status == "FAILURE":
            # 실패한 작업
            response["progress"] = 0
            response["message"] = "Task failed"
            if task.info:
                response["error"] = task.info.get("error", str(task.info))
                response["traceback"] = task.info.get("traceback")
            else:
                response["error"] = str(task.info)

        else:
            # 기타 상태
            response["message"] = f"Task status: {task.status}"

        logger.info("task_status_retrieved", task_id=task_id, status=task.status)

        return response

    except Exception as e:
        logger.error("get_task_status_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs")
async def stream_task_logs(task_id: str):
    """
    작업 로그 스트리밍 (Server-Sent Events)

    실시간으로 작업 진행 상황을 스트리밍합니다.
    """
    async def event_generator():
        """SSE 이벤트 생성기"""
        try:
            task = AsyncResult(task_id, app=celery_app)
            previous_status = None
            previous_progress = None

            # 작업이 완료될 때까지 폴링
            while not task.ready():
                current_status = task.status
                current_info = task.info if task.info else {}

                # 상태 또는 진행률이 변경된 경우에만 이벤트 전송
                current_progress = current_info.get("progress", 0)
                if current_status != previous_status or current_progress != previous_progress:
                    event_data = {
                        "task_id": task_id,
                        "status": current_status,
                        "progress": current_progress,
                        "message": current_info.get("message", "Processing...")
                    }

                    yield f"data: {json.dumps(event_data)}\n\n"

                    previous_status = current_status
                    previous_progress = current_progress

                await asyncio.sleep(1)  # 1초마다 폴링

            # 최종 결과 전송
            if task.successful():
                final_data = {
                    "task_id": task_id,
                    "status": "COMPLETED",
                    "progress": 100,
                    "message": "Task completed successfully",
                    "result": task.result
                }
            else:
                final_data = {
                    "task_id": task_id,
                    "status": "FAILURE",
                    "progress": 0,
                    "message": "Task failed",
                    "error": str(task.info) if task.info else "Unknown error"
                }

            yield f"data: {json.dumps(final_data)}\n\n"

            # 스트림 종료
            yield "event: close\ndata: Stream closed\n\n"

        except Exception as e:
            logger.error("log_streaming_failed", task_id=task_id, error=str(e))
            error_data = {
                "task_id": task_id,
                "status": "ERROR",
                "message": f"Streaming error: {str(e)}"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx 버퍼링 비활성화
        }
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    작업 취소

    실행 중인 작업을 취소합니다.
    """
    try:
        task = AsyncResult(task_id, app=celery_app)

        if task.status in ["PENDING", "LOADING", "PREPROCESSING", "TRAINING", "EVALUATING"]:
            task.revoke(terminate=True)
            logger.info("task_cancelled", task_id=task_id)
            return {
                "message": "Task cancelled",
                "task_id": task_id
            }
        else:
            return {
                "message": f"Task cannot be cancelled (status: {task.status})",
                "task_id": task_id,
                "status": task.status
            }

    except Exception as e:
        logger.error("task_cancellation_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    limit: int = Query(10, ge=1, le=100, description="최대 조회 수")
):
    """
    최근 작업 목록 조회

    Note: Celery는 기본적으로 작업 목록 조회 기능이 제한적입니다.
    실제 운영 환경에서는 별도의 데이터베이스에 작업 정보를 저장하는 것이 권장됩니다.
    """
    try:
        # Celery inspect를 사용하여 활성 작업 조회
        inspect = celery_app.control.inspect()

        active_tasks = inspect.active()
        reserved_tasks = inspect.reserved()
        scheduled_tasks = inspect.scheduled()

        tasks = {
            "active": active_tasks or {},
            "reserved": reserved_tasks or {},
            "scheduled": scheduled_tasks or {}
        }

        logger.info("tasks_listed")

        return tasks

    except Exception as e:
        logger.error("list_tasks_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers")
async def get_worker_stats():
    """
    Celery 워커 상태 조회

    워커의 건강 상태와 통계를 확인합니다.
    """
    try:
        inspect = celery_app.control.inspect()

        stats = inspect.stats()
        active_queues = inspect.active_queues()
        registered_tasks = inspect.registered()

        worker_info = {
            "stats": stats or {},
            "active_queues": active_queues or {},
            "registered_tasks": registered_tasks or {}
        }

        logger.info("worker_stats_retrieved")

        return worker_info

    except Exception as e:
        logger.error("get_worker_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
