"""Insight Agent - 모델 인사이트 및 비즈니스 해석"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import pandas as pd
import numpy as np

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.core.evaluation import SHAPAnalyzer
from app.config import settings


class InsightAgent(BaseAgent):
    """
    Insight Agent

    SHAP 분석 결과를 해석하고 LLM 기반 비즈니스 인사이트를 생성합니다.
    """

    @property
    def name(self) -> str:
        return "InsightAgent"

    @property
    def description(self) -> str:
        return "SHAP 분석 결과를 해석하고 비즈니스 인사이트를 생성합니다"

    async def run(self) -> AgentResult:
        """
        Insight Agent 실행

        Returns:
            AgentResult with insights data
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting Insight Agent")

            # 1. 모델 및 데이터 가져오기
            model_data = self.context.data.get("model_data")
            if not model_data:
                raise ValueError("Model data not found in context")

            model = model_data.get("model")
            X_train = model_data.get("X_train")
            X_test = model_data.get("X_test")
            y_test = model_data.get("y_test")
            predictions = model_data.get("predictions")

            if model is None or X_train is None or X_test is None:
                raise ValueError("Required model data missing")

            await self.emit_event("data_loaded", {
                "train_samples": len(X_train),
                "test_samples": len(X_test)
            })

            # 2. SHAP 분석 수행
            shap_results = await self._perform_shap_analysis(
                model, X_train, X_test
            )

            # 3. 오류 분석 수행
            error_analysis = await self._perform_error_analysis(
                X_test, y_test, predictions
            )

            # 4. LLM 기반 인사이트 생성
            insights = await self._generate_insights(
                shap_results,
                error_analysis,
                model_data
            )

            # 5. 결과 저장
            output_dir = os.path.join(
                settings.OUTPUTS_DIR,
                "insights",
                self.context.session_id
            )
            os.makedirs(output_dir, exist_ok=True)

            insights_file = os.path.join(output_dir, "insights.md")
            self._save_insights_report(insights, insights_file)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "shap_results": shap_results,
                    "error_analysis": error_analysis,
                    "insights": insights,
                    "insights_file": insights_file,
                },
                message="Insights generated successfully",
                metadata={
                    "duration": (self.end_time - self.start_time).total_seconds()
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Insight Agent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    async def _perform_shap_analysis(
        self,
        model,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        SHAP 분석 수행

        Args:
            model: 학습된 모델
            X_train: 학습 데이터
            X_test: 테스트 데이터

        Returns:
            SHAP 분석 결과
        """
        try:
            self.logger.info("Performing SHAP analysis")
            await self.emit_event("shap_analysis_started", {})

            # SHAP Analyzer 생성
            analyzer = SHAPAnalyzer(model, X_train, X_test)

            # SHAP 분석 수행
            output_dir = os.path.join(
                settings.OUTPUTS_DIR,
                "shap",
                self.context.session_id
            )

            report = analyzer.generate_analysis_report(output_dir)

            await self.emit_event("shap_analysis_completed", {
                "top_features_count": len(report.get("top_features", []))
            })

            return report

        except Exception as e:
            self.logger.error(f"SHAP analysis failed: {e}")

            # Fallback: 모델의 feature_importance 사용
            try:
                self.logger.info("Falling back to model feature_importance")

                # FLAML wrapper의 경우 내부 모델 추출
                actual_model = model
                if hasattr(model, 'model') and hasattr(model.model, 'feature_importances_'):
                    actual_model = model.model

                if hasattr(actual_model, 'feature_importances_'):
                    importances = actual_model.feature_importances_
                    feature_names = X_train.columns.tolist()

                    # Top 10 features
                    indices = np.argsort(importances)[::-1][:10]
                    top_features = [
                        {
                            "feature": feature_names[i],
                            "importance": float(importances[i])
                        }
                        for i in indices
                    ]

                    self.logger.info(f"Extracted {len(top_features)} features from model.feature_importances_")
                    return {
                        "top_features": top_features,
                        "method": "model_feature_importance",
                        "note": "SHAP analysis failed, using model's feature_importances_ instead"
                    }
            except Exception as e2:
                self.logger.error(f"Feature importance fallback also failed: {e2}")

            return {"error": str(e), "top_features": []}

    async def _perform_error_analysis(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        predictions: np.ndarray
    ) -> Dict[str, Any]:
        """
        오류 분석 수행

        Args:
            X_test: 테스트 데이터
            y_test: 실제 레이블
            predictions: 예측값

        Returns:
            오류 분석 결과
        """
        try:
            self.logger.info("Performing error analysis")

            if y_test is None or predictions is None:
                return {"error": "Missing y_test or predictions"}

            # 오류 샘플 식별
            if len(predictions.shape) > 1:
                # Binary classification - class 1 확률
                pred_labels = (predictions[:, 1] > 0.5).astype(int)
            else:
                pred_labels = predictions

            errors = pred_labels != y_test.values

            error_samples = X_test[errors]
            correct_samples = X_test[~errors]

            # 통계
            error_rate = errors.sum() / len(errors)

            # 오류 샘플의 특성 분석
            if len(error_samples) > 0:
                error_feature_means = error_samples.mean().to_dict()
                correct_feature_means = correct_samples.mean().to_dict()

                # 가장 차이나는 피처 찾기
                feature_diffs = {}
                for feature in error_samples.columns:
                    diff = abs(error_feature_means.get(feature, 0) - correct_feature_means.get(feature, 0))
                    feature_diffs[feature] = diff

                top_diff_features = sorted(feature_diffs.items(), key=lambda x: x[1], reverse=True)[:5]
            else:
                top_diff_features = []

            return {
                "error_rate": float(error_rate),
                "error_count": int(errors.sum()),
                "total_samples": int(len(errors)),
                "top_diff_features": [(f, float(d)) for f, d in top_diff_features]
            }

        except Exception as e:
            self.logger.error(f"Error analysis failed: {e}")
            return {"error": str(e)}

    async def _generate_insights(
        self,
        shap_results: Dict[str, Any],
        error_analysis: Dict[str, Any],
        model_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        LLM 기반 인사이트 생성

        Args:
            shap_results: SHAP 분석 결과
            error_analysis: 오류 분석 결과
            model_data: 모델 데이터

        Returns:
            인사이트 딕셔너리
        """
        try:
            self.logger.info("Generating LLM-based insights")

            # 프롬프트 생성
            prompt = self._create_insights_prompt(shap_results, error_analysis, model_data)

            # LLM 호출
            response = await self.generate(prompt, max_tokens=2000)

            # 응답 파싱
            insights_text = response.content

            # 구조화된 인사이트 추출
            insights = self._parse_insights(insights_text)

            # SHAP 및 오류 분석 결과 추가
            insights["shap_summary"] = shap_results.get("top_features", [])[:10]
            insights["error_summary"] = error_analysis

            return insights

        except Exception as e:
            self.logger.error(f"Failed to generate insights: {e}")
            return {
                "error": str(e),
                "raw_shap": shap_results,
                "raw_error": error_analysis
            }

    def _create_insights_prompt(
        self,
        shap_results: Dict[str, Any],
        error_analysis: Dict[str, Any],
        model_data: Dict[str, Any]
    ) -> str:
        """인사이트 생성 프롬프트 작성"""

        # Top features
        top_features = shap_results.get("top_features", [])[:10]
        features_text = "\n".join([
            f"- {f['feature']}: importance {f['importance']:.4f}"
            for f in top_features
        ])

        # Error analysis
        error_rate = error_analysis.get("error_rate", 0)
        top_diff_features = error_analysis.get("top_diff_features", [])
        diff_features_text = "\n".join([
            f"- {f}: diff {d:.4f}"
            for f, d in top_diff_features
        ])

        # Model metrics
        metrics = model_data.get("metrics", {})
        metrics_text = "\n".join([
            f"- {k}: {v:.4f}" if isinstance(v, float) else f"- {k}: {v}"
            for k, v in metrics.items()
        ])

        prompt = f"""다음은 머신러닝 모델의 분석 결과입니다.

## Top 10 Important Features (SHAP):
{features_text}

## Model Performance:
{metrics_text}

## Error Analysis:
- Error Rate: {error_rate:.2%}
- Top Different Features in Error Samples:
{diff_features_text}

이 분석 결과를 바탕으로 다음을 제공하세요:

1. **주요 발견사항** (3-5개)
   - 가장 중요한 피처들의 비즈니스적 의미
   - 모델 성능에 대한 해석

2. **비즈니스 인사이트** (3-5개)
   - 실무에 적용 가능한 구체적인 인사이트
   - 의사결정에 도움이 되는 해석

3. **개선 권장사항** (3개)
   - 모델 성능 개선 방안
   - 데이터 수집 또는 피처 엔지니어링 제안

4. **주의사항** (2-3개)
   - 모델 사용 시 유의할 점
   - 잠재적 한계 및 편향

간결하고 실용적으로 작성하세요.
"""

        return prompt

    def _parse_insights(self, insights_text: str) -> Dict[str, Any]:
        """인사이트 텍스트 파싱"""

        insights = {
            "full_text": insights_text,
            "key_findings": [],
            "business_insights": [],
            "recommendations": [],
            "warnings": []
        }

        # 간단한 섹션 파싱 (개선 가능)
        lines = insights_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 섹션 헤더 감지
            if "주요 발견사항" in line or "Key Findings" in line:
                current_section = "key_findings"
            elif "비즈니스 인사이트" in line or "Business Insights" in line:
                current_section = "business_insights"
            elif "개선 권장사항" in line or "Recommendations" in line:
                current_section = "recommendations"
            elif "주의사항" in line or "Warnings" in line or "주의" in line:
                current_section = "warnings"
            # 리스트 아이템
            elif line.startswith(('-', '*', '•')) and current_section:
                item = line[1:].strip()
                if item:
                    insights[current_section].append(item)

        return insights

    def _save_insights_report(self, insights: Dict[str, Any], output_file: str):
        """인사이트 리포트 저장"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Model Insights Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

            # Full text
            f.write("## Analysis\n\n")
            f.write(insights.get("full_text", ""))
            f.write("\n\n")

            # SHAP Summary
            f.write("## Top Features (SHAP)\n\n")
            for feature in insights.get("shap_summary", [])[:10]:
                f.write(f"- **{feature.get('feature')}**: {feature.get('importance', 0):.4f}\n")
            f.write("\n")

            # Error Summary
            error_summary = insights.get("error_summary", {})
            if error_summary:
                f.write("## Error Analysis\n\n")
                f.write(f"- Error Rate: {error_summary.get('error_rate', 0):.2%}\n")
                f.write(f"- Error Count: {error_summary.get('error_count', 0)}\n")
                f.write(f"- Total Samples: {error_summary.get('total_samples', 0)}\n")
                f.write("\n")

        self.logger.info(f"Insights report saved to {output_file}")
