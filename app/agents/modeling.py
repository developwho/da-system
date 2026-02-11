"""Modeling Agent - AutoML 모델 학습"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import json
import pandas as pd
import numpy as np

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.agents.contracts import normalize_problem_definition, normalize_research_results
from app.core.automl.flaml_wrapper import FLAMLWrapper
from app.storage.mlflow_tracker import MLflowTracker
from app.config import settings

# 리서치 추천 모델 → FLAML estimator 매핑
RESEARCH_MODEL_MAP: Dict[str, str] = {
    "xgboost": "xgboost",
    "xgb": "xgboost",
    "lightgbm": "lgbm",
    "lgbm": "lgbm",
    "catboost": "catboost",
    "random forest": "rf",
    "randomforest": "rf",
    "rf": "rf",
    "extra trees": "extra_tree",
    "extra_tree": "extra_tree",
    "gradient boosting": "xgboost",
    "gbm": "lgbm",
}


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

            self.logger.info("problem_definition_loaded",
                             file_id=file_id, target_column=target_column,
                             problem_type=problem_type)

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

            self.logger.info("target_stats",
                             y_dtype=str(y.dtype),
                             y_unique=int(y.nunique(dropna=False)))

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
            estimator_list = self._apply_research_recommendations(research_results)

            # 6. FLAML 설정
            config = {
                "task_type": self._map_problem_type(problem_type),
                "time_budget": 300,  # 5분 기본값
                "metric": self._get_metric(problem_type),
            }

            if estimator_list:
                config["estimator_list"] = estimator_list
                self.logger.info("using_recommended_models", models=estimator_list)

            # 6b. 불균형 처리: sample_weight
            sample_weight = None
            data_intel = self.context.data.get("data_intelligence", {})
            imbalance = data_intel.get("class_imbalance", {})
            if imbalance.get("detected") and imbalance.get("ratio", 1) > 5:
                from sklearn.utils.class_weight import compute_sample_weight
                try:
                    _, _, y_train_temp, _ = self._quick_split(X, y, problem_type)
                    sample_weight = compute_sample_weight("balanced", y_train_temp)
                    self.logger.info("using_sample_weight", ratio=imbalance.get("ratio"))
                except Exception as sw_err:
                    self.logger.warning("sample_weight_failed", error=str(sw_err))

            # 7. FLAML 학습
            flaml = FLAMLWrapper(config)
            result = flaml.train(X, y, sample_weight=sample_weight)

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

            # 9. Feature Importance → MLflow artifact로 저장
            feature_imp = result.get("feature_importance", {})
            if feature_imp:
                fi_list = [
                    {"feature": k, "importance": float(v), "ranking": i + 1}
                    for i, (k, v) in enumerate(
                        sorted(feature_imp.items(), key=lambda x: -x[1])
                        if isinstance(feature_imp, dict)
                        else enumerate(feature_imp)
                    )
                ]
                fi_dir = os.path.join(settings.OUTPUTS_DIR, "models", self.context.session_id)
                os.makedirs(fi_dir, exist_ok=True)
                fi_path = os.path.join(fi_dir, "feature_importance.json")
                with open(fi_path, "w", encoding="utf-8") as f:
                    json.dump(fi_list, f, ensure_ascii=False)
                try:
                    tracker.client.log_artifact(run_id, fi_path, artifact_path="analysis")
                    self.logger.info("feature_importance_logged", count=len(fi_list))
                except Exception as fi_exc:
                    self.logger.warning("feature_importance_log_failed", error=str(fi_exc))

            # 10. 모델 저장
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

            # 11. Insight Agent를 위한 데이터 준비 (FLAML에서 반환)
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
        """문제 유형에 따른 평가 메트릭 반환 — 사용자 선택 우선"""
        # 사용자가 Q&A에서 선택한 메트릭 우선
        problem_def = self.context.data.get("problem_definition") or {}
        user_metric = problem_def.get("evaluation_metric")
        if user_metric:
            # FLAML이 인식하는 형태로 정규화
            metric_alias = {
                "roc_auc": "roc_auc", "f1": "f1", "accuracy": "accuracy",
                "f1_macro": "macro_f1", "log_loss": "log_loss",
                "rmse": "rmse", "mae": "mae", "r2": "r2", "mape": "mape",
            }
            mapped = metric_alias.get(user_metric)
            if mapped:
                return mapped

        # 디폴트
        defaults = {
            "binary_classification": "roc_auc",
            "multiclass_classification": "accuracy",
            "regression": "rmse",
            "time_series": "mape",
        }
        return defaults.get(problem_type, "accuracy")

    def _apply_research_recommendations(self, research_results: Dict[str, Any]) -> List[str]:
        """리서치 추천 모델을 FLAML estimator_list로 매핑"""
        recommended = research_results.get("recommended_models", [])
        if not recommended:
            return []

        mapped = []
        for model_name in recommended:
            key = str(model_name).lower().strip()
            flaml_name = RESEARCH_MODEL_MAP.get(key)
            if flaml_name and flaml_name not in mapped:
                mapped.append(flaml_name)

        if not mapped:
            return []

        # 기본 estimator도 포함하여 안전성 확보
        for default in ["lgbm", "xgboost"]:
            if default not in mapped:
                mapped.append(default)

        self.logger.info("research_models_mapped", original=recommended[:5], mapped=mapped)
        return mapped

    def _quick_split(self, X, y, problem_type):
        """sample_weight 계산용 빠른 분할 (FLAML train 전)"""
        from sklearn.model_selection import train_test_split
        stratify = y if "classification" in (problem_type or "") else None
        try:
            return train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)
        except ValueError:
            return train_test_split(X, y, test_size=0.2, random_state=42)

    def _preprocess_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        피처 전처리 — 7단계 파이프라인

        1. DateTime → 수치 변환
        2. 이상치 클리핑 (IQR, outlier_pct > 5%)
        3. 스마트 범주형 인코딩 (저/중/고 카디널리티)
        4. 숫자 결측치 전략 (비율별)
        5. 근-제로-분산 컬럼 제거
        6. NaN 최종 정리
        7. 전처리 로그
        """
        X = X.copy()
        preprocess_log = []

        # ── Step 1: DateTime → 수치 변환 ──
        for col in X.columns:
            if pd.api.types.is_datetime64_any_dtype(X[col]):
                X[f"{col}_year"] = X[col].dt.year
                X[f"{col}_month"] = X[col].dt.month
                X[f"{col}_day_of_week"] = X[col].dt.dayofweek
                X[f"{col}_hour"] = X[col].dt.hour
                epoch = pd.Timestamp("1970-01-01")
                X[f"{col}_days_since_epoch"] = (X[col] - epoch).dt.days
                X = X.drop(columns=[col])
                preprocess_log.append(f"DateTime→수치: {col}")
            elif X[col].dtype == "object":
                # 날짜 문자열 감지 시도
                sample = X[col].dropna().head(20)
                if len(sample) > 0:
                    try:
                        converted = pd.to_datetime(sample, infer_datetime_format=True)
                        if converted.notna().sum() > len(sample) * 0.5:
                            X[col] = pd.to_datetime(X[col], errors="coerce")
                            epoch = pd.Timestamp("1970-01-01")
                            X[f"{col}_days"] = (X[col] - epoch).dt.days
                            X = X.drop(columns=[col])
                            preprocess_log.append(f"날짜문자열→수치: {col}")
                    except (ValueError, TypeError):
                        pass

        # ── Step 2: 이상치 클리핑 (DataIntelligence 결과 활용) ──
        data_intel = self.context.data.get("data_intelligence", {})
        outlier_report = data_intel.get("outlier_report", {})
        flagged_cols = outlier_report.get("flagged_columns", [])

        for col in flagged_cols:
            if col not in X.columns:
                continue
            col_info = outlier_report.get("columns", {}).get(col, {})
            lower = col_info.get("lower_bound")
            upper = col_info.get("upper_bound")
            if lower is not None and upper is not None:
                before_clip = len(X[(X[col] < lower) | (X[col] > upper)])
                X[col] = X[col].clip(lower=lower, upper=upper)
                preprocess_log.append(f"이상치 클리핑: {col} ({before_clip}건)")

        # ── Step 3: 스마트 범주형 인코딩 ──
        from sklearn.preprocessing import LabelEncoder
        cols_to_drop = []

        for col in X.columns:
            if X[col].dtype != "object":
                continue
            n_unique = X[col].nunique()

            if n_unique > len(X) * 0.5:
                # ID성 컬럼 — 드롭
                cols_to_drop.append(col)
                preprocess_log.append(f"ID성 컬럼 제거: {col} (고유값 {n_unique})")
            elif n_unique > 100:
                # 고카디널리티 — 드롭
                cols_to_drop.append(col)
                preprocess_log.append(f"고카디널리티 제거: {col} ({n_unique})")
            elif n_unique > 15:
                # 중카디널리티 — Frequency Encoding
                X[col] = X[col].fillna("__MISSING__")
                freq = X[col].value_counts(normalize=True)
                X[col] = X[col].map(freq).astype(float)
                preprocess_log.append(f"빈도 인코딩: {col} ({n_unique})")
            else:
                # 저카디널리티 — Label Encoding
                X[col] = X[col].fillna("__MISSING__")
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                preprocess_log.append(f"라벨 인코딩: {col} ({n_unique})")

        if cols_to_drop:
            X = X.drop(columns=cols_to_drop)

        # ── Step 4: 숫자 결측치 전략 ──
        numeric_cols = X.select_dtypes(include=["number"]).columns
        cols_to_drop_missing = []

        for col in numeric_cols:
            missing_pct = X[col].isnull().mean()
            if missing_pct == 0:
                continue
            elif missing_pct > 0.3:
                cols_to_drop_missing.append(col)
                preprocess_log.append(f"결측 과다 제거: {col} ({missing_pct:.0%})")
            elif missing_pct > 0.05:
                median = X[col].median()
                X[f"{col}_was_missing"] = X[col].isnull().astype(int)
                X[col] = X[col].fillna(median)
                preprocess_log.append(f"중앙값+지시자: {col} ({missing_pct:.0%})")
            else:
                X[col] = X[col].fillna(X[col].median())

        if cols_to_drop_missing:
            X = X.drop(columns=cols_to_drop_missing)

        # ── Step 5: 근-제로-분산 컬럼 제거 ──
        zero_var_cols = []
        for col in X.select_dtypes(include=["number"]).columns:
            if X[col].std() < 1e-8:
                zero_var_cols.append(col)
        if zero_var_cols:
            X = X.drop(columns=zero_var_cols)
            preprocess_log.append(f"제로분산 제거: {', '.join(zero_var_cols)}")

        # ── Step 6: NaN 최종 정리 ──
        if X.isnull().any().any():
            remaining = X.isnull().sum().sum()
            X = X.fillna(0)
            preprocess_log.append(f"잔여 NaN {remaining}건 → 0 대체")

        # ── Step 7: 로그 기록 ──
        if preprocess_log:
            self.logger.info("preprocessing_completed", steps=len(preprocess_log))
            for step in preprocess_log:
                self.logger.debug("preprocess_step", detail=step)

        # context에 전처리 로그 저장 (리포트용)
        self.update_context("preprocessing_log", preprocess_log)

        return X
