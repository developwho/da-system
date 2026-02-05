"""Modeling Agent - AutoML 모델 학습"""
from typing import Dict, Any, Optional
from datetime import datetime
import os
import json
import time
import pandas as pd

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.agents.contracts import normalize_problem_definition, normalize_research_results
from app.core.automl.flaml_wrapper import FLAMLWrapper
from app.storage.mlflow_tracker import MLflowTracker
from app.config import settings


class ModelingAgent(BaseAgent):
    """
    Modeling Agent

    FLAML AutoML을 사용하여 모델을 자동으로 학습하고 평가합니다.
    """

    @property
    def name(self) -> str:
        return "ModelingAgent"

    @property
    def description(self) -> str:
        return "FLAML AutoML을 사용하여 모델을 학습하고 평가합니다"

    async def run(self) -> AgentResult:
        """
        Modeling Agent 실행

        Returns:
            AgentResult with model data
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting Modeling Agent")

            # 1. 문제 정의에서 데이터 가져오기
            problem_definition = normalize_problem_definition(
                self.context.data.get("problem_definition") or {}
            )
            if not problem_definition:
                raise ValueError("Problem definition not found in context")

            file_id = problem_definition.get("file_id")
            target_column = problem_definition.get("target_column")
            problem_type = problem_definition.get("problem_type")

            if not file_id or not target_column:
                raise ValueError("file_id and target_column are required")

            # region agent log
            with open(r"d:\dasystem\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": self.context.session_id,
                    "runId": "pre-fix",
                    "hypothesisId": "H1",
                    "location": "app/agents/modeling.py:49",
                    "message": "problem_definition_loaded",
                    "data": {
                        "file_id": file_id,
                        "target_column": target_column,
                        "problem_type": problem_type,
                        "evaluation_metric": problem_definition.get("evaluation_metric"),
                    },
                    "timestamp": int(time.time() * 1000),
                }, ensure_ascii=False) + "\n")
            # endregion

            await self.emit_event("data_loading", {"file_id": file_id})

            # 2. 데이터 로드
            from app.storage.file_manager import FileManager
            from app.core.data_pipeline.loader import DataLoader

            file_path = FileManager.get_file_path(file_id)
            df, metadata = DataLoader.load_file(file_path)

            self.logger.info("data_loaded", rows=len(df), columns=len(df.columns))

            # 3. 타겟 변수 분리
            if target_column not in df.columns:
                raise ValueError(f"Target column '{target_column}' not found in data")

            X = df.drop(columns=[target_column])
            y = df[target_column]

            # region agent log
            with open(r"d:\dasystem\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": self.context.session_id,
                    "runId": "pre-fix",
                    "hypothesisId": "H1",
                    "location": "app/agents/modeling.py:76",
                    "message": "target_stats",
                    "data": {
                        "y_dtype": str(y.dtype),
                        "y_unique": int(y.nunique(dropna=False)),
                        "y_sample": [str(v) for v in y.dropna().unique()[:5]],
                    },
                    "timestamp": int(time.time() * 1000),
                }, ensure_ascii=False) + "\n")
            # endregion

            # 4. 데이터 전처리
            X = self._preprocess_features(X)

            await self.emit_event("training_started", {
                "problem_type": problem_type,
                "samples": len(X),
                "features": len(X.columns)
            })

            # 5. Research 결과에서 추천 모델 가져오기 (있으면)
            research_results = normalize_research_results(
                self.context.data.get("research_results", {})
            )
            recommended_models = research_results.get("recommended_models", [])

            # 6. FLAML 설정
            config = {
                "task_type": self._map_problem_type(problem_type),
                "time_budget": 300,  # 5분 기본값
                "metric": self._get_metric(problem_type),
            }

            if recommended_models:
                config["estimator_list"] = recommended_models
                self.logger.info("using_recommended_models", models=recommended_models)

            # 7. FLAML 학습
            flaml = FLAMLWrapper(config)
            result = flaml.train(X, y)

            await self.emit_event("training_completed", {
                "best_estimator": result.get("best_estimator"),
                "metrics": result.get("metrics")
            })

            # 8. MLflow 로깅
            tracker = MLflowTracker()
            run_id = tracker.log_experiment(
                experiment_name=f"session_{self.context.session_id}",
                params=flaml.get_params(),
                metrics=result["metrics"],
                model=flaml.model,
                tags={
                    "session_id": self.context.session_id,
                    "file_id": file_id,
                    "target_column": target_column,
                    "problem_type": problem_type
                }
            )

            # 9. 모델 저장
            model_dir = os.path.join(
                settings.OUTPUTS_DIR,
                "models",
                self.context.session_id
            )
            os.makedirs(model_dir, exist_ok=True)
            model_path = flaml.save_model(model_dir)

            self.logger.info("model_saved", model_path=model_path, mlflow_run_id=run_id)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            # 10. Insight Agent를 위한 데이터 준비 (FLAML에서 반환)
            X_train = result.get("X_train")
            X_test = result.get("X_test")
            y_train = result.get("y_train")
            y_test = result.get("y_test")
            predictions = result.get("predictions")

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "model_path": model_path,
                    "mlflow_run_id": run_id,
                    "problem_type": problem_type,
                    "metrics": result["metrics"],
                    "best_estimator": result["best_estimator"],
                    "feature_importance": result.get("feature_importance", []),
                    "training_time": result.get("training_duration", 0),
                    # Insight Agent를 위한 데이터
                    "model_data": {
                        "model": flaml.model,
                        "X_train": X_train,
                        "X_test": X_test,
                        "y_train": y_train,
                        "y_test": y_test,
                        "predictions": predictions,
                        "feature_names": list(X.columns)
                    }
                },
                message=f"Model trained successfully (estimator: {result['best_estimator']})",
                metadata={
                    "duration": (self.end_time - self.start_time).total_seconds()
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Modeling Agent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    def _map_problem_type(self, problem_type: str) -> str:
        """문제 유형을 FLAML task_type으로 매핑"""
        mapping = {
            "binary_classification": "classification",
            "multiclass_classification": "classification",
            "regression": "regression",
            "time_series": "ts_forecast"
        }
        return mapping.get(problem_type, "classification")

    def _get_metric(self, problem_type: str) -> str:
        """문제 유형에 따른 평가 메트릭 반환"""
        if problem_type == "binary_classification":
            return "roc_auc"
        if problem_type == "multiclass_classification":
            return "accuracy"
        if problem_type == "regression":
            return "rmse"
        if problem_type == "time_series":
            return "mape"
        return "accuracy"

    def _preprocess_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        피처 전처리

        - Object/Categorical 컬럼 처리
        - 결측치 처리
        - 불필요한 컬럼 제거
        """
        X = X.copy()

        # 1. 고유값이 너무 많은 컬럼 제거 (ID성 컬럼)
        for col in X.columns:
            if X[col].dtype == 'object':
                n_unique = X[col].nunique()
                if n_unique > len(X) * 0.5:  # 50% 이상 유니크하면 ID로 간주
                    self.logger.info(f"dropping_high_cardinality_column", column=col, n_unique=n_unique)
                    X = X.drop(columns=[col])

        # 2. Numeric 아닌 컬럼 처리
        for col in X.columns:
            if X[col].dtype == 'object':
                # Label Encoding (간단한 방법)
                from sklearn.preprocessing import LabelEncoder
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                self.logger.info(f"label_encoded_column", column=col)

        # 3. 결측치 처리
        if X.isnull().any().any():
            # Numeric: 중앙값으로 채우기
            numeric_cols = X.select_dtypes(include=['number']).columns
            for col in numeric_cols:
                if X[col].isnull().any():
                    X[col].fillna(X[col].median(), inplace=True)

            self.logger.info("missing_values_filled")

        return X
