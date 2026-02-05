"""
MLflow 실험 추적 및 모델 레지스트리
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.models.signature import infer_signature
import pandas as pd

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MLflowTracker:
    """MLflow 실험 추적 및 모델 관리"""

    def __init__(self, tracking_uri: str = None):
        """
        MLflow Tracker 초기화

        Args:
            tracking_uri: MLflow tracking URI (기본값: settings.MLFLOW_TRACKING_URI)
        """
        self.tracking_uri = tracking_uri or settings.MLFLOW_TRACKING_URI
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

        logger.info("mlflow_tracker_initialized", tracking_uri=self.tracking_uri)

    def create_experiment(self, experiment_name: str, artifact_location: str = None) -> str:
        """
        실험 생성 (이미 존재하면 기존 ID 반환)

        Args:
            experiment_name: 실험 이름
            artifact_location: artifact 저장 위치 (선택)

        Returns:
            experiment_id
        """
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment:
                logger.info("experiment_exists", name=experiment_name, id=experiment.experiment_id)
                return experiment.experiment_id
            else:
                experiment_id = mlflow.create_experiment(
                    name=experiment_name,
                    artifact_location=artifact_location
                )
                logger.info("experiment_created", name=experiment_name, id=experiment_id)
                return experiment_id
        except Exception as e:
            logger.error("experiment_creation_failed", error=str(e))
            raise

    def log_experiment(
        self,
        experiment_name: str,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        model: Any = None,
        artifacts: Dict[str, str] = None,
        tags: Dict[str, str] = None,
        model_signature: Any = None,
        registered_model_name: str = None
    ) -> str:
        """
        실험 로깅 (파라미터, 메트릭, 모델, artifacts)

        Args:
            experiment_name: 실험 이름
            params: 파라미터 딕셔너리
            metrics: 메트릭 딕셔너리
            model: 학습된 모델 객체
            artifacts: artifact 파일 경로 딕셔너리 {이름: 경로}
            tags: 태그 딕셔너리
            model_signature: 모델 시그니처 (자동 추론 가능)
            registered_model_name: 모델 레지스트리 등록 이름

        Returns:
            run_id
        """
        try:
            # 실험 생성 또는 조회
            experiment_id = self.create_experiment(experiment_name)

            # Run 시작
            with mlflow.start_run(experiment_id=experiment_id) as run:
                run_id = run.info.run_id

                # 파라미터 로깅
                if params:
                    # MLflow는 파라미터 값을 문자열로만 받음
                    str_params = {k: str(v) for k, v in params.items()}
                    mlflow.log_params(str_params)
                    logger.info("params_logged", count=len(params))

                # 메트릭 로깅
                if metrics:
                    mlflow.log_metrics(metrics)
                    logger.info("metrics_logged", count=len(metrics), metrics=metrics)

                # 태그 설정
                if tags:
                    mlflow.set_tags(tags)
                    logger.info("tags_set", count=len(tags))

                # Artifacts 로깅
                if artifacts:
                    for name, path in artifacts.items():
                        if os.path.isfile(path):
                            mlflow.log_artifact(path, artifact_path=name)
                        elif os.path.isdir(path):
                            mlflow.log_artifacts(path, artifact_path=name)
                    logger.info("artifacts_logged", count=len(artifacts))

                # 모델 로깅
                if model:
                    mlflow.sklearn.log_model(
                        sk_model=model,
                        artifact_path="model",
                        signature=model_signature,
                        registered_model_name=registered_model_name
                    )
                    logger.info(
                        "model_logged",
                        registered_model_name=registered_model_name
                    )

                logger.info(
                    "experiment_logged_successfully",
                    experiment_name=experiment_name,
                    run_id=run_id
                )

                return run_id

        except Exception as e:
            logger.error("experiment_logging_failed", error=str(e))
            raise

    def log_model_with_signature(
        self,
        model: Any,
        X_sample: pd.DataFrame,
        y_sample: pd.Series = None,
        artifact_path: str = "model",
        registered_model_name: str = None
    ) -> str:
        """
        모델 시그니처 자동 추론 후 로깅

        Args:
            model: 학습된 모델
            X_sample: 입력 샘플 데이터프레임
            y_sample: 출력 샘플 (선택)
            artifact_path: artifact 경로
            registered_model_name: 레지스트리 등록 이름

        Returns:
            artifact_uri
        """
        try:
            # 시그니처 추론
            if y_sample is not None:
                predictions = model.predict(X_sample)
                signature = infer_signature(X_sample, predictions)
            else:
                signature = infer_signature(X_sample)

            # 모델 로깅
            model_info = mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path=artifact_path,
                signature=signature,
                registered_model_name=registered_model_name
            )

            logger.info(
                "model_logged_with_signature",
                artifact_uri=model_info.model_uri
            )

            return model_info.model_uri

        except Exception as e:
            logger.error("model_logging_with_signature_failed", error=str(e))
            raise

    def get_run(self, run_id: str) -> mlflow.entities.Run:
        """Run 정보 조회"""
        try:
            run = self.client.get_run(run_id)
            return run
        except Exception as e:
            logger.error("get_run_failed", run_id=run_id, error=str(e))
            raise

    def get_experiment_runs(
        self,
        experiment_name: str,
        max_results: int = 100,
        order_by: List[str] = None
    ) -> List[mlflow.entities.Run]:
        """
        실험의 모든 Run 조회

        Args:
            experiment_name: 실험 이름
            max_results: 최대 결과 수
            order_by: 정렬 기준 (예: ["metrics.roc_auc DESC"])

        Returns:
            Run 리스트
        """
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if not experiment:
                logger.warning("experiment_not_found", name=experiment_name)
                return []

            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=max_results,
                order_by=order_by or ["start_time DESC"]
            )

            logger.info("experiment_runs_retrieved", count=len(runs))
            return runs

        except Exception as e:
            logger.error("get_experiment_runs_failed", error=str(e))
            raise

    def get_best_run(
        self,
        experiment_name: str,
        metric: str = "roc_auc",
        ascending: bool = False
    ) -> Optional[mlflow.entities.Run]:
        """
        최고 성능 Run 조회

        Args:
            experiment_name: 실험 이름
            metric: 메트릭 이름
            ascending: 오름차순 여부 (기본값: False, 내림차순)

        Returns:
            최고 성능 Run
        """
        try:
            order = "ASC" if ascending else "DESC"
            runs = self.get_experiment_runs(
                experiment_name,
                max_results=1,
                order_by=[f"metrics.{metric} {order}"]
            )

            if runs:
                best_run = runs[0]
                logger.info(
                    "best_run_found",
                    run_id=best_run.info.run_id,
                    metric=metric,
                    value=best_run.data.metrics.get(metric)
                )
                return best_run
            else:
                logger.warning("no_runs_found", experiment_name=experiment_name)
                return None

        except Exception as e:
            logger.error("get_best_run_failed", error=str(e))
            raise

    def load_model(self, run_id: str, artifact_path: str = "model") -> Any:
        """
        Run에서 모델 로드

        Args:
            run_id: Run ID
            artifact_path: 모델 artifact 경로

        Returns:
            로드된 모델
        """
        try:
            model_uri = f"runs:/{run_id}/{artifact_path}"
            model = mlflow.sklearn.load_model(model_uri)

            logger.info("model_loaded", run_id=run_id, artifact_path=artifact_path)
            return model

        except Exception as e:
            logger.error("model_load_failed", run_id=run_id, error=str(e))
            raise

    def register_model(
        self,
        run_id: str,
        model_name: str,
        artifact_path: str = "model"
    ) -> str:
        """
        모델을 레지스트리에 등록

        Args:
            run_id: Run ID
            model_name: 등록할 모델 이름
            artifact_path: 모델 artifact 경로

        Returns:
            모델 버전
        """
        try:
            model_uri = f"runs:/{run_id}/{artifact_path}"
            model_version = mlflow.register_model(model_uri, model_name)

            logger.info(
                "model_registered",
                name=model_name,
                version=model_version.version
            )

            return model_version.version

        except Exception as e:
            logger.error("model_registration_failed", error=str(e))
            raise

    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str
    ):
        """
        모델 스테이지 전환

        Args:
            model_name: 모델 이름
            version: 모델 버전
            stage: 스테이지 ("Staging", "Production", "Archived")
        """
        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage
            )

            logger.info(
                "model_stage_transitioned",
                name=model_name,
                version=version,
                stage=stage
            )

        except Exception as e:
            logger.error("model_stage_transition_failed", error=str(e))
            raise

    def get_model_version(self, model_name: str, stage: str = "Production") -> Any:
        """
        특정 스테이지의 모델 로드

        Args:
            model_name: 모델 이름
            stage: 스테이지 ("Staging", "Production")

        Returns:
            로드된 모델
        """
        try:
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.sklearn.load_model(model_uri)

            logger.info(
                "model_loaded_from_stage",
                name=model_name,
                stage=stage
            )

            return model

        except Exception as e:
            logger.error("model_load_from_stage_failed", error=str(e))
            raise

    def delete_run(self, run_id: str):
        """Run 삭제"""
        try:
            self.client.delete_run(run_id)
            logger.info("run_deleted", run_id=run_id)
        except Exception as e:
            logger.error("run_deletion_failed", run_id=run_id, error=str(e))
            raise

    def delete_experiment(self, experiment_id: str):
        """실험 삭제"""
        try:
            self.client.delete_experiment(experiment_id)
            logger.info("experiment_deleted", experiment_id=experiment_id)
        except Exception as e:
            logger.error("experiment_deletion_failed", error=str(e))
            raise

    def search_runs_by_tags(
        self,
        experiment_name: str,
        tags: Dict[str, str],
        max_results: int = 100
    ) -> List[mlflow.entities.Run]:
        """
        태그로 Run 검색

        Args:
            experiment_name: 실험 이름
            tags: 검색할 태그 딕셔너리
            max_results: 최대 결과 수

        Returns:
            Run 리스트
        """
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if not experiment:
                return []

            # 태그 필터 생성
            filter_string = " and ".join([
                f"tags.{key} = '{value}'" for key, value in tags.items()
            ])

            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string=filter_string,
                max_results=max_results
            )

            logger.info("runs_found_by_tags", count=len(runs), tags=tags)
            return runs

        except Exception as e:
            logger.error("search_runs_by_tags_failed", error=str(e))
            raise

    def compare_runs(
        self,
        run_ids: List[str],
        metrics: List[str] = None
    ) -> pd.DataFrame:
        """
        여러 Run 비교

        Args:
            run_ids: Run ID 리스트
            metrics: 비교할 메트릭 리스트 (None이면 모든 메트릭)

        Returns:
            비교 결과 데이터프레임
        """
        try:
            comparison_data = []

            for run_id in run_ids:
                run = self.client.get_run(run_id)

                row = {
                    "run_id": run_id,
                    "start_time": run.info.start_time,
                    "status": run.info.status
                }

                # 메트릭 추가
                if metrics:
                    for metric in metrics:
                        row[metric] = run.data.metrics.get(metric)
                else:
                    row.update(run.data.metrics)

                # 주요 파라미터 추가
                row["estimator"] = run.data.params.get("best_estimator")
                row["task_type"] = run.data.params.get("task_type")

                comparison_data.append(row)

            df = pd.DataFrame(comparison_data)

            logger.info("runs_compared", count=len(run_ids))
            return df

        except Exception as e:
            logger.error("run_comparison_failed", error=str(e))
            raise
