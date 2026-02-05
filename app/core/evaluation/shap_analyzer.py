"""SHAP 기반 모델 설명 및 분석"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 백엔드 비활성화
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SHAPAnalyzer:
    """SHAP 기반 모델 해석 및 분석"""

    def __init__(self, model, X_train: pd.DataFrame, X_test: pd.DataFrame):
        """
        Args:
            model: 학습된 모델
            X_train: 학습 데이터
            X_test: 테스트 데이터
        """
        self.model = model
        self.X_train = X_train
        self.X_test = X_test
        self.explainer = None
        self.shap_values = None
        self.expected_value = None

    def create_explainer(self, explainer_type: str = "auto") -> None:
        """
        SHAP Explainer 생성

        Args:
            explainer_type: Explainer 타입 (auto, tree, kernel, linear)
        """
        try:
            logger.info(f"Creating SHAP explainer: {explainer_type}")

            if explainer_type == "auto":
                # 모델 타입에 따라 자동 선택
                if hasattr(self.model, "predict_proba"):
                    # Tree-based models (XGBoost, LightGBM, etc.)
                    try:
                        # FLAML wrapper의 경우 내부 모델 추출 시도
                        actual_model = self.model
                        if hasattr(self.model, 'model') and hasattr(self.model.model, 'predict'):
                            actual_model = self.model.model
                            logger.info("Extracted inner model from FLAML wrapper")

                        self.explainer = shap.TreeExplainer(actual_model)
                        logger.info("Using TreeExplainer")
                    except Exception as e1:
                        logger.warning(f"TreeExplainer failed: {e1}")
                        # Fallback to KernelExplainer
                        try:
                            self.explainer = shap.KernelExplainer(
                                self.model.predict_proba,
                                shap.sample(self.X_train, 100)
                            )
                            logger.info("Using KernelExplainer (fallback)")
                        except Exception as e2:
                            logger.warning(f"KernelExplainer failed: {e2}")
                            # Final fallback: feature importance만 사용
                            raise Exception(f"All SHAP explainers failed. TreeExplainer: {e1}, KernelExplainer: {e2}")
                else:
                    self.explainer = shap.Explainer(self.model, self.X_train)
                    logger.info("Using generic Explainer")
            elif explainer_type == "tree":
                self.explainer = shap.TreeExplainer(self.model)
            elif explainer_type == "kernel":
                self.explainer = shap.KernelExplainer(
                    self.model.predict,
                    shap.sample(self.X_train, 100)
                )
            elif explainer_type == "linear":
                self.explainer = shap.LinearExplainer(self.model, self.X_train)
            else:
                raise ValueError(f"Unknown explainer type: {explainer_type}")

        except Exception as e:
            logger.error(f"Failed to create SHAP explainer: {e}")
            raise

    def calculate_shap_values(self, max_samples: int = 1000) -> np.ndarray:
        """
        SHAP values 계산

        Args:
            max_samples: 최대 샘플 수 (성능을 위해 제한)

        Returns:
            SHAP values array
        """
        try:
            if self.explainer is None:
                self.create_explainer()

            logger.info(f"Calculating SHAP values for {len(self.X_test)} samples")

            # 샘플 수 제한
            X_sample = self.X_test.sample(min(max_samples, len(self.X_test)), random_state=42)

            # SHAP values 계산
            self.shap_values = self.explainer.shap_values(X_sample)

            # Expected value 저장
            if hasattr(self.explainer, "expected_value"):
                self.expected_value = self.explainer.expected_value
            else:
                self.expected_value = None

            logger.info("SHAP values calculated successfully")
            return self.shap_values

        except Exception as e:
            logger.error(f"Failed to calculate SHAP values: {e}")
            raise

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Feature Importance 계산 (SHAP 기반)

        Args:
            top_n: 상위 N개 피처

        Returns:
            Feature importance DataFrame
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Calculating feature importance (top {top_n})")

            # SHAP values의 절대값 평균으로 중요도 계산
            if isinstance(self.shap_values, list):
                # Binary classification - class 1의 SHAP values 사용
                shap_array = self.shap_values[1]
            else:
                shap_array = self.shap_values

            # Feature importance
            feature_importance = np.abs(shap_array).mean(axis=0)

            # DataFrame 생성
            importance_df = pd.DataFrame({
                'feature': self.X_test.columns,
                'importance': feature_importance
            }).sort_values('importance', ascending=False)

            return importance_df.head(top_n)

        except Exception as e:
            logger.error(f"Failed to get feature importance: {e}")
            raise

    def plot_summary(self, output_path: str, max_display: int = 20) -> str:
        """
        SHAP Summary Plot 생성

        Args:
            output_path: 출력 파일 경로
            max_display: 표시할 최대 피처 수

        Returns:
            저장된 파일 경로
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Creating SHAP summary plot: {output_path}")

            plt.figure(figsize=(10, 8))

            # SHAP values 선택
            if isinstance(self.shap_values, list):
                shap_array = self.shap_values[1]
            else:
                shap_array = self.shap_values

            # Summary plot
            shap.summary_plot(
                shap_array,
                self.X_test.sample(min(1000, len(self.X_test)), random_state=42),
                max_display=max_display,
                show=False
            )

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Summary plot saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create summary plot: {e}")
            raise

    def plot_bar(self, output_path: str, max_display: int = 20) -> str:
        """
        SHAP Bar Plot 생성 (Feature Importance)

        Args:
            output_path: 출력 파일 경로
            max_display: 표시할 최대 피처 수

        Returns:
            저장된 파일 경로
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Creating SHAP bar plot: {output_path}")

            plt.figure(figsize=(10, 8))

            # SHAP values 선택
            if isinstance(self.shap_values, list):
                shap_array = self.shap_values[1]
            else:
                shap_array = self.shap_values

            # Bar plot
            shap.summary_plot(
                shap_array,
                self.X_test.sample(min(1000, len(self.X_test)), random_state=42),
                plot_type="bar",
                max_display=max_display,
                show=False
            )

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Bar plot saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create bar plot: {e}")
            raise

    def plot_waterfall(
        self,
        sample_idx: int,
        output_path: str
    ) -> str:
        """
        SHAP Waterfall Plot 생성 (개별 예측 설명)

        Args:
            sample_idx: 샘플 인덱스
            output_path: 출력 파일 경로

        Returns:
            저장된 파일 경로
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Creating SHAP waterfall plot: {output_path}")

            # SHAP values 선택
            if isinstance(self.shap_values, list):
                shap_array = self.shap_values[1]
            else:
                shap_array = self.shap_values

            # Waterfall plot
            plt.figure(figsize=(10, 8))

            # Explanation 객체 생성
            explanation = shap.Explanation(
                values=shap_array[sample_idx],
                base_values=self.expected_value if not isinstance(self.expected_value, list) else self.expected_value[1],
                data=self.X_test.iloc[sample_idx].values,
                feature_names=self.X_test.columns.tolist()
            )

            shap.waterfall_plot(explanation, show=False)

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Waterfall plot saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create waterfall plot: {e}")
            raise

    def plot_force(
        self,
        sample_idx: int,
        output_path: str
    ) -> str:
        """
        SHAP Force Plot 생성 (개별 예측 설명)

        Args:
            sample_idx: 샘플 인덱스
            output_path: 출력 파일 경로 (.html)

        Returns:
            저장된 파일 경로
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Creating SHAP force plot: {output_path}")

            # SHAP values 선택
            if isinstance(self.shap_values, list):
                shap_array = self.shap_values[1]
                expected_val = self.expected_value[1] if isinstance(self.expected_value, list) else self.expected_value
            else:
                shap_array = self.shap_values
                expected_val = self.expected_value

            # Force plot HTML 생성
            force_plot = shap.force_plot(
                expected_val,
                shap_array[sample_idx],
                self.X_test.iloc[sample_idx],
                matplotlib=False
            )

            # HTML 저장
            shap.save_html(output_path, force_plot)

            logger.info(f"Force plot saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create force plot: {e}")
            raise

    def explain_prediction(
        self,
        sample_idx: int,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        개별 예측 설명

        Args:
            sample_idx: 샘플 인덱스
            top_n: 상위 N개 피처

        Returns:
            설명 딕셔너리
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Explaining prediction for sample {sample_idx}")

            # SHAP values 선택
            if isinstance(self.shap_values, list):
                shap_array = self.shap_values[1]
            else:
                shap_array = self.shap_values

            # 샘플의 SHAP values
            sample_shap = shap_array[sample_idx]
            sample_data = self.X_test.iloc[sample_idx]

            # 중요도 순으로 정렬
            feature_contributions = pd.DataFrame({
                'feature': self.X_test.columns,
                'value': sample_data.values,
                'shap_value': sample_shap,
                'abs_shap': np.abs(sample_shap)
            }).sort_values('abs_shap', ascending=False)

            top_features = feature_contributions.head(top_n)

            return {
                'sample_index': sample_idx,
                'top_features': top_features.to_dict('records'),
                'total_shap_value': float(np.sum(sample_shap)),
                'expected_value': float(self.expected_value if not isinstance(self.expected_value, list) else self.expected_value[1])
            }

        except Exception as e:
            logger.error(f"Failed to explain prediction: {e}")
            raise

    def analyze_feature_interactions(
        self,
        feature1: str,
        feature2: str,
        output_path: str
    ) -> str:
        """
        Feature Interaction 분석

        Args:
            feature1: 첫 번째 피처
            feature2: 두 번째 피처
            output_path: 출력 파일 경로

        Returns:
            저장된 파일 경로
        """
        try:
            if self.shap_values is None:
                self.calculate_shap_values()

            logger.info(f"Analyzing interaction: {feature1} vs {feature2}")

            plt.figure(figsize=(10, 8))

            # SHAP values 선택
            if isinstance(self.shap_values, list):
                shap_array = self.shap_values[1]
            else:
                shap_array = self.shap_values

            # Dependence plot
            shap.dependence_plot(
                feature1,
                shap_array,
                self.X_test.sample(min(1000, len(self.X_test)), random_state=42),
                interaction_index=feature2,
                show=False
            )

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            logger.info(f"Interaction plot saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to analyze feature interaction: {e}")
            raise

    def generate_analysis_report(self, output_dir: str) -> Dict[str, Any]:
        """
        종합 분석 리포트 생성

        Args:
            output_dir: 출력 디렉토리

        Returns:
            리포트 메타데이터
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Generating SHAP analysis report in {output_dir}")

            # 1. Feature Importance
            importance_df = self.get_feature_importance(top_n=20)
            importance_file = output_path / "feature_importance.csv"
            importance_df.to_csv(importance_file, index=False)

            # 2. Summary Plot
            summary_plot = self.plot_summary(str(output_path / "shap_summary.png"))

            # 3. Bar Plot
            bar_plot = self.plot_bar(str(output_path / "shap_bar.png"))

            # 4. Waterfall Plot (샘플 예시)
            waterfall_plot = self.plot_waterfall(0, str(output_path / "shap_waterfall_sample.png"))

            # 5. Force Plot (샘플 예시)
            force_plot = self.plot_force(0, str(output_path / "shap_force_sample.html"))

            report_metadata = {
                'feature_importance_file': str(importance_file),
                'summary_plot': summary_plot,
                'bar_plot': bar_plot,
                'waterfall_plot': waterfall_plot,
                'force_plot': force_plot,
                'top_features': importance_df.head(10).to_dict('records')
            }

            logger.info("SHAP analysis report generated successfully")
            return report_metadata

        except Exception as e:
            logger.error(f"Failed to generate analysis report: {e}")
            raise
