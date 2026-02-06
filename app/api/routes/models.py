"""
Models API 라우트
모델 관리 및 예측
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import os
import json

from app.utils.logger import get_logger
from app.storage.mlflow_tracker import MLflowTracker
from app.api.deps import require_api_key
from app.config import settings

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = get_logger(__name__)


# Pydantic 스키마
class ModelSummary(BaseModel):
    """모델 요약 정보"""
    run_id: str
    experiment_name: Optional[str] = None
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    best_estimator: Optional[str] = None
    problem_type: Optional[str] = None
    metrics: Dict[str, float] = {}


class ModelDetail(BaseModel):
    """모델 상세 정보"""
    run_id: str
    experiment_name: Optional[str] = None
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    artifact_uri: Optional[str] = None

    # 학습 정보
    params: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}
    tags: Dict[str, str] = {}

    # 모델 정보
    best_estimator: Optional[str] = None
    problem_type: Optional[str] = None
    target_column: Optional[str] = None

    # Feature Importance (있는 경우)
    feature_importance: Optional[List[Dict[str, Any]]] = None


class PredictRequest(BaseModel):
    """예측 요청"""
    data: List[Dict[str, Any]]  # 입력 데이터 (레코드 형식)


class PredictResponse(BaseModel):
    """예측 응답"""
    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None  # 분류의 경우
    run_id: str
    model_info: Dict[str, Any]


@router.get("", response_model=List[ModelSummary])
async def list_models(
    experiment_name: Optional[str] = Query(None, description="실험 이름 필터"),
    limit: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
    order_by: Optional[str] = Query(None, description="정렬 기준 (예: metrics.roc_auc DESC)")
):
    """
    모델 목록 조회

    MLflow에 저장된 모든 모델(Run)을 조회합니다.
    """
    try:
        tracker = MLflowTracker()

        if experiment_name:
            # 특정 실험의 run들만 조회
            order_by_list = [order_by] if order_by else None
            runs = tracker.get_experiment_runs(
                experiment_name=experiment_name,
                max_results=limit,
                order_by=order_by_list
            )
            experiment_names = [experiment_name] * len(runs)
        else:
            # 모든 실험의 run들 조회
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            # 모든 실험 조회
            experiments = client.search_experiments()
            all_runs = []
            experiment_names = []

            for exp in experiments:
                if exp.lifecycle_stage == "active":
                    runs = tracker.get_experiment_runs(
                        experiment_name=exp.name,
                        max_results=limit,
                        order_by=[order_by] if order_by else None
                    )
                    all_runs.extend(runs)
                    experiment_names.extend([exp.name] * len(runs))

            runs = all_runs[:limit]
            experiment_names = experiment_names[:limit]

        # 응답 생성
        models = []
        for run, exp_name in zip(runs, experiment_names):
            model_summary = ModelSummary(
                run_id=run.info.run_id,
                experiment_name=exp_name,
                status=run.info.status,
                start_time=datetime.fromtimestamp(run.info.start_time / 1000).isoformat() if run.info.start_time else None,
                end_time=datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
                best_estimator=run.data.params.get("best_estimator"),
                problem_type=run.data.params.get("problem_type") or run.data.params.get("task_type"),
                metrics=dict(run.data.metrics)
            )
            models.append(model_summary)

        logger.info("models_listed", count=len(models))
        return models

    except Exception as e:
        logger.error("list_models_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.get("/{run_id}", response_model=ModelDetail)
async def get_model_info(run_id: str):
    """
    모델 상세 정보 조회

    특정 Run의 상세 정보를 조회합니다.
    """
    try:
        tracker = MLflowTracker()
        run = tracker.get_run(run_id)

        if not run:
            raise HTTPException(status_code=404, detail=f"Model not found: {run_id}")

        # Experiment 이름 조회
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        experiment = client.get_experiment(run.info.experiment_id)

        # Feature Importance: artifact에서 먼저 시도, 없으면 params fallback
        feature_importance = None
        try:
            artifact_uri = run.info.artifact_uri or ""
            # MLflow file store uses file:/// prefix
            artifact_base = artifact_uri.replace("file:///", "").replace("file:", "")
            fi_artifact_path = os.path.join(artifact_base, "analysis", "feature_importance.json")
            if os.path.exists(fi_artifact_path):
                with open(fi_artifact_path, "r", encoding="utf-8") as f:
                    feature_importance = json.load(f)
        except Exception:
            pass
        # Fallback: check params (legacy)
        if not feature_importance and "feature_importance" in run.data.params:
            try:
                feature_importance = json.loads(run.data.params["feature_importance"])
            except Exception:
                pass

        model_detail = ModelDetail(
            run_id=run.info.run_id,
            experiment_name=experiment.name if experiment else None,
            status=run.info.status,
            start_time=datetime.fromtimestamp(run.info.start_time / 1000).isoformat() if run.info.start_time else None,
            end_time=datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
            artifact_uri=run.info.artifact_uri,
            params=dict(run.data.params),
            metrics=dict(run.data.metrics),
            tags=dict(run.data.tags),
            best_estimator=run.data.params.get("best_estimator"),
            problem_type=run.data.params.get("problem_type") or run.data.params.get("task_type"),
            target_column=run.data.params.get("target_column"),
            feature_importance=feature_importance
        )

        logger.info("model_info_retrieved", run_id=run_id)
        return model_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_model_info_failed", run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


@router.post("/{run_id}/predict", response_model=PredictResponse)
async def predict(run_id: str, request: PredictRequest):
    """
    예측 수행

    저장된 모델을 로드하여 예측을 수행합니다.
    """
    try:
        tracker = MLflowTracker()

        # 모델 로드
        logger.info("loading_model", run_id=run_id)
        model = tracker.load_model(run_id)

        # Run 정보 조회
        run = tracker.get_run(run_id)
        problem_type = run.data.params.get("problem_type") or run.data.params.get("task_type")

        # 입력 데이터를 DataFrame으로 변환
        input_df = pd.DataFrame(request.data)
        logger.info("input_data_prepared", shape=input_df.shape)

        # 예측 수행
        predictions = model.predict(input_df)

        # 확률 예측 (분류 문제의 경우)
        probabilities = None
        if problem_type in ["binary_classification", "multiclass_classification", "classification"]:
            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba(input_df).tolist()

        # NumPy 타입을 Python 타입으로 변환
        predictions_list = []
        for pred in predictions:
            if isinstance(pred, (np.integer, np.floating)):
                predictions_list.append(float(pred))
            else:
                predictions_list.append(pred)

        response = PredictResponse(
            predictions=predictions_list,
            probabilities=probabilities,
            run_id=run_id,
            model_info={
                "best_estimator": run.data.params.get("best_estimator"),
                "problem_type": problem_type,
                "metrics": dict(run.data.metrics)
            }
        )

        logger.info("prediction_completed", run_id=run_id, n_predictions=len(predictions_list))
        return response

    except HTTPException:
        raise
    except FileNotFoundError:
        logger.error("model_not_found", run_id=run_id)
        raise HTTPException(status_code=404, detail=f"Model not found: {run_id}")
    except Exception as e:
        logger.error("prediction_failed", run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/{run_id}/explain")
async def explain_predictions(
    run_id: str,
    top_n: int = Query(10, ge=1, le=50, description="상위 N개 중요 피처")
):
    """
    모델 설명 (Feature Importance)

    SHAP 분석 결과 또는 Feature Importance를 반환합니다.
    """
    try:
        tracker = MLflowTracker()
        run = tracker.get_run(run_id)

        if not run:
            raise HTTPException(status_code=404, detail=f"Model not found: {run_id}")

        # Feature Importance: artifact에서 먼저 시도, 없으면 params fallback
        feature_importance = None
        try:
            artifact_uri = run.info.artifact_uri or ""
            artifact_base = artifact_uri.replace("file:///", "").replace("file:", "")
            fi_artifact_path = os.path.join(artifact_base, "analysis", "feature_importance.json")
            if os.path.exists(fi_artifact_path):
                with open(fi_artifact_path, "r", encoding="utf-8") as f:
                    feature_importance = json.load(f)
        except Exception:
            pass
        if not feature_importance and "feature_importance" in run.data.params:
            try:
                feature_importance = json.loads(run.data.params["feature_importance"])
            except Exception:
                pass

        # SHAP artifacts 조회 (outputs/shap/{session_id}/)
        session_id = run.data.tags.get("session_id")
        if session_id:
            shap_dir = os.path.join(settings.OUTPUTS_DIR, "shap", session_id)
            if os.path.exists(shap_dir):
                # SHAP 결과 파일 목록
                shap_files = [f for f in os.listdir(shap_dir) if f.endswith(('.png', '.json'))]

                return {
                    "run_id": run_id,
                    "feature_importance": feature_importance[:top_n] if feature_importance else None,
                    "shap_artifacts": shap_files,
                    "shap_directory": shap_dir
                }

        return {
            "run_id": run_id,
            "feature_importance": feature_importance[:top_n] if feature_importance else None,
            "message": "SHAP analysis not available for this model"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("explain_predictions_failed", run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")
