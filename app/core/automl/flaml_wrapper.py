"""
FLAML AutoML 래퍼
자동 모델 선택 및 하이퍼파라미터 튜닝
"""
import os
import pickle
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from flaml import AutoML

from app.utils.logger import get_logger

logger = get_logger(__name__)


class FLAMLWrapper:
    """FLAML AutoML 래퍼 클래스"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        FLAML 래퍼 초기화

        Args:
            config: FLAML 설정
                - task_type: "binary_classification", "multiclass_classification", "regression", "timeseries"
                - time_budget: 학습 시간 제한 (초)
                - metric: 평가 메트릭
                - estimator_list: 사용할 모델 리스트
        """
        self.config = config or {}
        self.task_type = self.config.get("task_type", "binary_classification")
        self.automl: Optional[AutoML] = None
        self.model = None
        self.best_config = None

        logger.info("flaml_wrapper_initialized", task_type=self.task_type)

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        progress_callback: Callable[[float], None] = None,
        sample_weight: np.ndarray = None
    ) -> Dict[str, Any]:
        """
        모델 학습

        Args:
            X: 피처 데이터프레임
            y: 타겟 시리즈
            progress_callback: 진행률 콜백 함수
            sample_weight: 불균형 처리용 샘플 가중치

        Returns:
            학습 결과
        """
        logger.info("flaml_training_started", rows=len(X), columns=len(X.columns))

        # Train/Test 분할 (분류 문제 시 층화추출)
        is_classification = "classification" in self.task_type
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42,
                stratify=y if is_classification else None
            )
        except ValueError:
            # 층화 실패 시 (클래스당 샘플 부족 등) 일반 분할
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

        # sample_weight도 동일하게 분할
        sw_train = None
        if sample_weight is not None and len(sample_weight) == len(X):
            train_idx = X_train.index
            sw_train = sample_weight[X.index.get_indexer(train_idx)]
            if (sw_train < 0).any() or np.isnan(sw_train).any():
                sw_train = None
                logger.warning("sample_weight_invalid_after_split")

        # FLAML 설정 생성
        flaml_config = self._get_flaml_config()

        logger.debug("flaml_config_built",
                      task_type=self.task_type,
                      flaml_task=flaml_config.get("task"),
                      metric=flaml_config.get("metric"))

        # AutoML 객체 생성
        self.automl = AutoML()

        # 학습 시작
        fit_kwargs = dict(
            X_train=X_train,
            y_train=y_train,
            **flaml_config
        )
        if sw_train is not None:
            fit_kwargs["sample_weight"] = sw_train

        self.automl.fit(**fit_kwargs)

        # 최적 모델 저장
        self.model = self.automl.model
        self.best_config = self.automl.best_config

        # 모델 학습 실패 확인
        if self.model is None or self.automl.best_estimator is None:
            logger.error("flaml_training_failed_no_model", best_loss=self.automl.best_loss)
            raise ValueError(
                "FLAML failed to train any model. "
                "This could be due to: (1) insufficient time budget, "
                "(2) data issues, or (3) metric/estimator configuration problems. "
                f"Best loss: {self.automl.best_loss}"
            )

        # 테스트 데이터로 평가
        metrics = self._evaluate(X_test, y_test)

        # Feature Importance 추출
        feature_importance = self._get_feature_importance(X.columns)

        logger.info(
            "flaml_training_completed",
            best_estimator=self.automl.best_estimator,
            best_loss=self.automl.best_loss
        )

        # FLAML의 학습 시간 계산
        training_duration = getattr(self.automl, 'training_duration', None)
        if training_duration is None:
            # FLAML 2.x에서는 time_to_find_best_model 사용
            training_duration = getattr(self.automl, 'time_to_find_best_model', 0)

        return {
            "best_estimator": self.automl.best_estimator,
            "best_config": self.best_config,
            "metrics": metrics,
            "feature_importance": feature_importance,
            "training_duration": training_duration,
            # Insight Agent를 위한 데이터 추가
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test,
            "predictions": self.automl.predict(X_test)
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        예측 수행

        Args:
            X: 피처 데이터프레임

        Returns:
            예측 결과
        """
        if self.automl is None:
            raise ValueError("Model not trained yet. Call train() first.")

        return self.automl.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        확률 예측 (분류 문제만 해당)

        Args:
            X: 피처 데이터프레임

        Returns:
            확률 예측 결과
        """
        if self.automl is None:
            raise ValueError("Model not trained yet. Call train() first.")

        if "classification" not in self.task_type:
            raise ValueError("predict_proba is only available for classification tasks")

        return self.automl.predict_proba(X)

    def save_model(self, path: str) -> str:
        """
        모델 저장

        Args:
            path: 저장 경로

        Returns:
            모델 ID
        """
        if self.automl is None:
            raise ValueError("No model to save")

        # 디렉토리 생성
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 모델 파일 경로
        model_file = save_dir / "model.pkl"

        # 모델 저장
        with open(model_file, "wb") as f:
            pickle.dump({
                "automl": self.automl,
                "config": self.config,
                "task_type": self.task_type,
                "best_config": self.best_config
            }, f)

        logger.info("model_saved", path=str(model_file))

        return str(save_dir)

    @classmethod
    def load_model(cls, path: str) -> "FLAMLWrapper":
        """
        모델 로드

        Args:
            path: 모델 디렉토리 경로

        Returns:
            FLAMLWrapper 인스턴스
        """
        model_file = Path(path) / "model.pkl"

        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")

        with open(model_file, "rb") as f:
            data = pickle.load(f)

        wrapper = cls(config=data["config"])
        wrapper.automl = data["automl"]
        wrapper.task_type = data["task_type"]
        wrapper.best_config = data.get("best_config")
        wrapper.model = wrapper.automl.model if wrapper.automl else None

        logger.info("model_loaded", path=str(model_file))

        return wrapper

    def get_params(self) -> Dict[str, Any]:
        """모델 파라미터 조회"""
        if self.automl is None:
            return {}

        # FLAML의 학습 시간 계산
        training_duration = getattr(self.automl, 'training_duration', None)
        if training_duration is None:
            training_duration = getattr(self.automl, 'time_to_find_best_model', 0)

        return {
            "task_type": self.task_type,
            "best_estimator": self.automl.best_estimator,
            "best_config": self.best_config,
            "training_duration": training_duration
        }

    def _get_flaml_config(self) -> Dict[str, Any]:
        """FLAML 설정 생성"""
        # 태스크 타입 매핑
        task_map = {
            "binary_classification": "classification",
            "multiclass_classification": "classification",
            "regression": "regression",
            "timeseries": "ts_forecast"
        }

        flaml_task = task_map.get(self.task_type, "classification")

        # 메트릭 선택
        metric = self.config.get("metric") or self._get_default_metric()

        # Estimator 리스트
        estimator_list = self.config.get("estimator_list") or self._get_default_estimators()

        # 시간 제한
        time_budget = self.config.get("time_budget", 3600)  # 기본 1시간

        config = {
            "task": flaml_task,
            "metric": metric,
            "estimator_list": estimator_list,
            "time_budget": time_budget,
            "early_stop": True,
            "verbose": 3,
            "n_jobs": -1,  # 모든 CPU 사용
            "seed": 42
        }

        logger.info("flaml_config_created", config=config)

        return config

    def _get_default_metric(self) -> str:
        """태스크 타입별 기본 메트릭"""
        metric_map = {
            "binary_classification": "roc_auc",
            "multiclass_classification": "accuracy",
            "regression": "r2",
            "timeseries": "mape"
        }
        return metric_map.get(self.task_type, "roc_auc")

    def _get_default_estimators(self) -> list:
        """태스크 타입별 기본 Estimator 리스트"""
        estimator_map = {
            "binary_classification": ["lgbm", "xgboost", "catboost", "rf", "extra_tree"],
            "multiclass_classification": ["lgbm", "xgboost", "catboost", "rf"],
            "regression": ["lgbm", "xgboost", "catboost", "rf", "extra_tree"],
            "timeseries": ["prophet", "arima"]
        }
        return estimator_map.get(self.task_type, ["lgbm", "xgboost"])

    def _evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """모델 평가"""
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
            mean_squared_error, mean_absolute_error, r2_score
        )

        y_pred = self.automl.predict(X_test)

        metrics = {}

        if "classification" in self.task_type:
            metrics["accuracy"] = float(accuracy_score(y_test, y_pred))

            if self.task_type == "binary_classification":
                y_pred_proba = self.automl.predict_proba(X_test)[:, 1]
                metrics["roc_auc"] = float(roc_auc_score(y_test, y_pred_proba))
                metrics["precision"] = float(precision_score(y_test, y_pred, zero_division=0))
                metrics["recall"] = float(recall_score(y_test, y_pred, zero_division=0))
                metrics["f1"] = float(f1_score(y_test, y_pred, zero_division=0))
            else:
                metrics["precision_weighted"] = float(
                    precision_score(y_test, y_pred, average="weighted", zero_division=0)
                )
                metrics["recall_weighted"] = float(
                    recall_score(y_test, y_pred, average="weighted", zero_division=0)
                )
                metrics["f1_weighted"] = float(
                    f1_score(y_test, y_pred, average="weighted", zero_division=0)
                )

        elif self.task_type == "regression":
            metrics["rmse"] = float(np.sqrt(mean_squared_error(y_test, y_pred)))
            metrics["mae"] = float(mean_absolute_error(y_test, y_pred))
            metrics["r2"] = float(r2_score(y_test, y_pred))

        return metrics

    def _get_feature_importance(self, feature_names: list) -> Dict[str, float]:
        """Feature Importance 추출"""
        if self.model is None:
            return {}

        try:
            # Tree 기반 모델의 feature_importances_
            if hasattr(self.model, "feature_importances_"):
                importances = self.model.feature_importances_
                total = importances.sum()
                if total > 0:
                    importances = importances / total
                return dict(zip(feature_names, importances.tolist()))

            # 선형 모델의 coef_
            elif hasattr(self.model, "coef_"):
                coef = self.model.coef_
                if len(coef.shape) > 1:
                    coef = np.abs(coef).mean(axis=0)
                abs_coef = np.abs(coef)
                total = abs_coef.sum()
                if total > 0:
                    abs_coef = abs_coef / total
                return dict(zip(feature_names, abs_coef.tolist()))

        except Exception as e:
            logger.warning("feature_importance_extraction_failed", error=str(e))

        return {}

    def evaluate(self, df: pd.DataFrame, target_column: str = None) -> Dict[str, Any]:
        """
        데이터프레임으로 평가

        Args:
            df: 평가 데이터
            target_column: 타겟 변수명

        Returns:
            평가 메트릭
        """
        if target_column and target_column in df.columns:
            X = df.drop(columns=[target_column])
            y = df[target_column]
            return self._evaluate(X, y)
        else:
            # 예측만 수행
            y_pred = self.predict(df)
            return {"predictions": y_pred.tolist()}
