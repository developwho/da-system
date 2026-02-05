"""
모델링 Celery 태스크
FLAML AutoML 학습 및 평가
"""
from celery import Task
from typing import Dict, Any
import traceback

from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelingTask(Task):
    """모델링 태스크 베이스 클래스"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """작업 실패 시 호출"""
        logger.error(
            "modeling_task_failed",
            task_id=task_id,
            exception=str(exc),
            traceback=str(einfo)
        )

    def on_success(self, retval, task_id, args, kwargs):
        """작업 성공 시 호출"""
        logger.info("modeling_task_success", task_id=task_id)


@celery_app.task(
    bind=True,
    base=ModelingTask,
    name="app.tasks.modeling_tasks.train_automl_model"
)
def train_automl_model(
    self,
    file_id: str,
    target_column: str,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    AutoML 모델 학습

    Args:
        file_id: 데이터 파일 ID
        target_column: 타겟 변수명
        config: FLAML 설정 (선택)

    Returns:
        학습 결과
    """
    try:
        logger.info(
            "automl_training_started",
            task_id=self.request.id,
            file_id=file_id,
            target_column=target_column
        )

        # 진행 상황 업데이트
        self.update_state(
            state="LOADING",
            meta={"progress": 10, "message": "데이터 로딩 중..."}
        )

        # 데이터 로드
        from app.storage.file_manager import FileManager
        from app.core.data_pipeline.loader import DataLoader

        file_path = FileManager.get_file_path(file_id)
        df, metadata = DataLoader.load_file(file_path)

        logger.info("data_loaded", rows=len(df), columns=len(df.columns))

        # 진행 상황 업데이트
        self.update_state(
            state="PREPROCESSING",
            meta={"progress": 20, "message": "데이터 전처리 중..."}
        )

        # 타겟 변수 분리
        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found")

        X = df.drop(columns=[target_column])
        y = df[target_column]

        # 문제 유형 감지
        from app.core.data_pipeline.type_detector import TypeDetector

        task_detection = TypeDetector.detect_task_type(df, target_column)
        task_type = task_detection["task_type"]

        logger.info("task_type_detected", task_type=task_type)

        # 진행 상황 업데이트
        self.update_state(
            state="TRAINING",
            meta={
                "progress": 30,
                "message": f"모델 학습 중... (Task: {task_type})"
            }
        )

        # FLAML 학습
        from app.core.automl.flaml_wrapper import FLAMLWrapper

        config = config or {}
        config["task_type"] = task_type

        flaml = FLAMLWrapper(config)

        # 학습 시작
        result = flaml.train(X, y, progress_callback=lambda p: self.update_state(
            state="TRAINING",
            meta={"progress": 30 + int(p * 0.5), "message": f"학습 진행 중... {p:.1f}%"}
        ))

        # 진행 상황 업데이트
        self.update_state(
            state="EVALUATING",
            meta={"progress": 85, "message": "모델 평가 중..."}
        )

        # MLflow 로깅
        from app.storage.mlflow_tracker import MLflowTracker

        tracker = MLflowTracker()
        run_id = tracker.log_experiment(
            experiment_name=f"automl_{file_id}",
            params=flaml.get_params(),
            metrics=result["metrics"],
            model=flaml.model,
            tags={
                "file_id": file_id,
                "target_column": target_column,
                "task_type": task_type,
                "task_id": self.request.id
            }
        )

        # 모델 저장
        model_id = flaml.save_model(f"outputs/models/{file_id}")

        # 진행 상황 업데이트
        self.update_state(
            state="COMPLETED",
            meta={"progress": 100, "message": "학습 완료!"}
        )

        logger.info(
            "automl_training_completed",
            task_id=self.request.id,
            model_id=model_id,
            mlflow_run_id=run_id
        )

        return {
            "status": "success",
            "model_id": model_id,
            "mlflow_run_id": run_id,
            "task_type": task_type,
            "metrics": result["metrics"],
            "best_estimator": result["best_estimator"]
        }

    except Exception as e:
        logger.error(
            "automl_training_error",
            task_id=self.request.id,
            error=str(e),
            traceback=traceback.format_exc()
        )

        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "traceback": traceback.format_exc()}
        )

        raise


@celery_app.task(name="app.tasks.modeling_tasks.evaluate_model")
def evaluate_model(model_id: str, test_file_id: str) -> Dict[str, Any]:
    """
    모델 평가

    Args:
        model_id: 모델 ID
        test_file_id: 테스트 데이터 파일 ID

    Returns:
        평가 결과
    """
    try:
        logger.info("model_evaluation_started", model_id=model_id)

        # 모델 로드
        from app.core.automl.flaml_wrapper import FLAMLWrapper

        flaml = FLAMLWrapper.load_model(f"outputs/models/{model_id}")

        # 테스트 데이터 로드
        from app.storage.file_manager import FileManager
        from app.core.data_pipeline.loader import DataLoader

        file_path = FileManager.get_file_path(test_file_id)
        df, _ = DataLoader.load_file(file_path)

        # 평가
        result = flaml.evaluate(df)

        logger.info("model_evaluation_completed", model_id=model_id)

        return {
            "status": "success",
            "model_id": model_id,
            "metrics": result
        }

    except Exception as e:
        logger.error("model_evaluation_error", error=str(e))
        raise
