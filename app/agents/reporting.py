"""Reporting Agent - 종합 리포트 생성"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import shutil
import base64
from pathlib import Path
import json

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.agents.report_template import McKinseyReportTemplate
from app.config import settings


class ReportingAgent(BaseAgent):
    """
    Reporting Agent

    전체 분석 결과를 Markdown 및 HTML 리포트로 생성합니다.
    """

    @property
    def name(self) -> str:
        return "ReportingAgent"

    @property
    def description(self) -> str:
        return "전체 분석 결과를 Markdown 및 HTML 리포트로 생성합니다"

    async def run(self) -> AgentResult:
        """
        Reporting Agent 실행

        Returns:
            AgentResult with report data
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting Reporting Agent")

            # 1. 전체 데이터 수집
            report_data = self._collect_report_data()

            # 2. Markdown 리포트 생성
            markdown_report = await self._generate_markdown_report(report_data)

            # 3. HTML 리포트 생성
            html_report = await self._generate_html_report(report_data)

            # 4. Artifacts 패키징
            artifacts_zip = self._package_artifacts(report_data)

            # 5. 메타데이터 저장
            metadata_file = self._save_metadata(report_data)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "markdown_report": markdown_report,
                    "html_report": html_report,
                    "artifacts_zip": artifacts_zip,
                    "metadata_file": metadata_file,
                },
                message="Reports generated successfully",
                metadata={
                    "duration": (self.end_time - self.start_time).total_seconds()
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Reporting Agent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    def _collect_report_data(self) -> Dict[str, Any]:
        """리포트 데이터 수집"""

        report_data = {
            "session_id": self.context.session_id,
            "timestamp": datetime.now().isoformat(),
            "problem_definition": self.context.data.get("problem_definition", {}),
            "research_results": self.context.data.get("research_results", {}),
            "model_data": self.context.data.get("model_data", {}),
            "insights": self.context.data.get("insights", {}),
            "data_intelligence": self.context.data.get("data_intelligence", {}),
            "preprocessing_log": self.context.data.get("preprocessing_log", []),
            "data_profile": self.context.data.get("data_profile", {}),
        }

        return report_data

    async def _generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """
        Markdown 리포트 생성

        Args:
            report_data: 리포트 데이터

        Returns:
            Markdown 파일 경로
        """
        try:
            self.logger.info("Generating Markdown report")

            output_dir = os.path.join(
                settings.OUTPUTS_DIR,
                "reports",
                self.context.session_id
            )
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(output_dir, "report.md")

            with open(output_file, "w", encoding="utf-8") as f:
                # Title
                f.write("# Data Analysis Report\n\n")
                f.write(f"**Session ID:** {report_data['session_id']}\n\n")
                f.write(f"**Generated:** {report_data['timestamp']}\n\n")
                f.write("---\n\n")

                # 1. Executive Summary
                f.write("## 1. Executive Summary\n\n")
                summary = await self._generate_executive_summary(report_data)
                self._cached_executive_summary = summary
                f.write(summary)
                f.write("\n\n")

                # 2. Problem Definition
                f.write("## 2. Problem Definition\n\n")
                self._write_problem_definition(f, report_data.get("problem_definition", {}))

                # 3. Research Findings
                f.write("## 3. Prior Research\n\n")
                self._write_research_findings(f, report_data.get("research_results", {}))

                # 4. Data Quality
                f.write("## 4. Data Quality & Preprocessing\n\n")
                self._write_data_quality_section(f, report_data)

                # 5. Data Analysis
                f.write("## 5. Data Analysis\n\n")
                self._write_data_analysis(f, report_data)

                # 6. Modeling
                f.write("## 6. Modeling\n\n")
                self._write_modeling_section(f, report_data.get("model_data", {}))

                # 7. Model Insights
                f.write("## 7. Model Insights\n\n")
                self._write_insights_section(f, report_data.get("insights", {}))

                # 8. Research Comparison
                f.write("## 8. Research Comparison\n\n")
                self._write_research_comparison(f, report_data)

                # 9. Recommendations
                f.write("## 9. Recommendations\n\n")
                self._write_recommendations(f, report_data)

                # 10. Appendix
                f.write("## 10. Appendix\n\n")
                self._write_appendix(f, report_data)

            self.logger.info(f"Markdown report saved to {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"Failed to generate Markdown report: {e}")
            raise

    async def _generate_executive_summary(self, report_data: Dict[str, Any]) -> str:
        """Executive Summary 생성 (LLM 사용) — 도메인 맞춤"""

        try:
            problem_def = report_data.get("problem_definition", {})
            model_data = report_data.get("model_data", {})
            insights = report_data.get("insights", {})
            data_intel = report_data.get("data_intelligence", {})

            problem_type = problem_def.get("problem_type", "N/A")
            goal = problem_def.get("analysis_goal") or problem_def.get("goal", "N/A")
            metrics = model_data.get("metrics", {})
            key_findings = insights.get("key_findings", [])

            # 도메인 컨텍스트
            domain_ctx = ""
            domain_info = data_intel.get("domain", {})
            if domain_info and domain_info.get("domain", "general") != "general":
                domain_ctx = f"\n**Domain:** {domain_info['domain']} (confidence: {domain_info.get('confidence', 'N/A')})"

            # 리서치 벤치마크
            research = report_data.get("research_results", {})
            research_ctx = ""
            research_summary = research.get("summary", "")
            if research_summary and len(research_summary) > 20:
                research_ctx = f"\n**Research Benchmark:** {research_summary[:300]}"

            prompt = f"""다음 데이터 분석 프로젝트의 Executive Summary를 작성하세요.

**Problem Type:** {problem_type}
**Goal:** {goal}{domain_ctx}{research_ctx}

**Model Performance:**
{json.dumps(metrics, indent=2)}

**Key Findings:**
{chr(10).join([f"- {f}" for f in key_findings[:5]])}

2-3 문단으로 비기술적 경영진을 위한 수준으로 작성하세요:
1. 프로젝트 목표 및 접근 방법
2. 주요 결과 및 성능 (선행연구 대비 비교 가능 시 포함)
3. 핵심 인사이트 및 비즈니스 가치

간결하고 임원에게 보고하는 형식으로 작성하세요.
"""

            response = await self.generate(prompt, max_tokens=600, temperature=0.5)
            return response.content

        except Exception as e:
            self.logger.error(f"Failed to generate executive summary: {e}")
            return "Executive summary generation failed."

    def _write_problem_definition(self, f, problem_def: Dict[str, Any]):
        """Problem Definition 섹션 작성"""

        f.write(f"**Problem Type:** {problem_def.get('problem_type', 'N/A')}\n\n")
        f.write(f"**Goal:** {problem_def.get('analysis_goal') or problem_def.get('goal', 'N/A')}\n\n")
        f.write(f"**Target Variable:** {problem_def.get('target_column') or problem_def.get('target_variable', 'N/A')}\n\n")
        f.write(f"**Evaluation Metric:** {problem_def.get('evaluation_metric', 'N/A')}\n\n")

    def _write_research_findings(self, f, research_results: Dict[str, Any]):
        """Research Findings 섹션 작성"""

        # Papers
        papers = research_results.get("papers", [])
        if papers:
            f.write("### Papers\n\n")
            f.write(f"Found {len(papers)} relevant papers.\n\n")

        # Kaggle
        kaggle = research_results.get("kaggle_solutions") or research_results.get("kaggle", {})
        if kaggle:
            f.write("### Kaggle Solutions\n\n")
            competition = kaggle.get("competition", {})
            f.write(f"**Competition:** {competition.get('title', 'N/A')}\n\n")
            techniques = kaggle.get("techniques", [])
            if techniques:
                f.write("**Techniques:**\n")
                for tech in techniques[:10]:
                    f.write(f"- {tech}\n")
                f.write("\n")

        # DeepResearch
        deep_research = research_results.get("deep_research", {})
        if deep_research:
            f.write("### Deep Research\n\n")
            summary = deep_research.get("summary", "N/A")
            f.write(f"{summary[:500]}...\n\n")

    def _write_data_analysis(self, f, report_data: Dict[str, Any]):
        """Data Analysis 섹션 작성"""

        problem_def = report_data.get("problem_definition", {})
        data_chars = problem_def.get("data_characteristics", {})

        if data_chars:
            f.write(f"**Rows:** {data_chars.get('n_rows', 'N/A')}\n\n")
            f.write(f"**Columns:** {data_chars.get('n_columns', 'N/A')}\n\n")
            f.write(f"**Missing Values:** {data_chars.get('missing_values', 'N/A')}\n\n")

    def _write_modeling_section(self, f, model_data: Dict[str, Any]):
        """Modeling 섹션 작성"""

        best_estimator = model_data.get("best_estimator") or model_data.get("best_model", "N/A")
        f.write(f"**Best Model:** {best_estimator}\n\n")

        metrics = model_data.get("metrics", {})
        if metrics:
            f.write("**Performance Metrics:**\n\n")
            for key, value in metrics.items():
                if isinstance(value, float):
                    f.write(f"- {key}: {value:.4f}\n")
                else:
                    f.write(f"- {key}: {value}\n")
            f.write("\n")

    def _write_insights_section(self, f, insights: Dict[str, Any]):
        """Insights 섹션 작성"""

        # Key Findings
        key_findings = insights.get("key_findings", [])
        if key_findings:
            f.write("### Key Findings\n\n")
            for finding in key_findings:
                f.write(f"- {finding}\n")
            f.write("\n")

        # Business Insights
        business_insights = insights.get("business_insights", [])
        if business_insights:
            f.write("### Business Insights\n\n")
            for insight in business_insights:
                f.write(f"- {insight}\n")
            f.write("\n")

    def _write_recommendations(self, f, report_data: Dict[str, Any]):
        """Recommendations 섹션 작성"""

        insights = report_data.get("insights", {})
        recommendations = insights.get("recommendations", [])

        if recommendations:
            for rec in recommendations:
                f.write(f"- {rec}\n")
            f.write("\n")
        else:
            f.write("No specific recommendations at this time.\n\n")

    def _write_data_quality_section(self, f, report_data: Dict[str, Any]):
        """Data Quality & Preprocessing 섹션 작성"""
        data_intel = report_data.get("data_intelligence", {})
        preprocessing_log = report_data.get("preprocessing_log", [])

        # 도메인 감지
        domain = data_intel.get("domain", {})
        if domain and domain.get("domain", "general") != "general":
            f.write(f"**Detected Domain:** {domain['domain']} (confidence: {domain.get('confidence', 'N/A')})\n\n")

        # 불균형 분석
        imbalance = data_intel.get("class_imbalance", {})
        if imbalance and imbalance.get("severity"):
            f.write(f"**Class Imbalance:** {imbalance['severity']} (ratio {imbalance.get('ratio', 'N/A')}:1, minority {imbalance.get('minority_pct', 'N/A')}%)\n\n")

        # 이상치 요약
        outliers = data_intel.get("outlier_report", {})
        if outliers:
            flagged = [col for col, info in outliers.items()
                       if isinstance(info, dict) and info.get("outlier_pct", 0) > 5]
            if flagged:
                f.write(f"**Outlier Columns ({len(flagged)}):** {', '.join(flagged[:10])}\n\n")

        # 전처리 로그
        if preprocessing_log:
            f.write("### Applied Preprocessing Steps\n\n")
            for step in preprocessing_log:
                f.write(f"- {step}\n")
            f.write("\n")

        # 데이터 경고
        warnings = data_intel.get("data_warnings", [])
        if warnings:
            f.write("### Data Warnings\n\n")
            for w in warnings:
                f.write(f"- {w}\n")
            f.write("\n")

        if not data_intel and not preprocessing_log:
            f.write("No data quality analysis available.\n\n")

    def _write_research_comparison(self, f, report_data: Dict[str, Any]):
        """Research Comparison 섹션 — 테이블 형태"""
        research = report_data.get("research_results", {})
        model_data = report_data.get("model_data", {})
        metrics = model_data.get("metrics", {})

        # 추천 모델과 기법
        recommended = research.get("recommended_models", [])
        techniques = research.get("techniques", [])

        if not research or (not recommended and not techniques):
            f.write("No prior research data available for comparison.\n\n")
            return

        # 기법 테이블
        if techniques:
            f.write("### Identified Techniques from Research\n\n")
            f.write("| Source | Techniques |\n")
            f.write("|--------|------------|\n")

            papers = research.get("papers", [])
            kaggle = research.get("kaggle_solutions") or research.get("kaggle", {})
            deep = research.get("deep_research", {})

            if papers:
                f.write(f"| HuggingFace Papers | {len(papers)} papers reviewed |\n")
            if kaggle and kaggle.get("techniques"):
                f.write(f"| Kaggle Solutions | {', '.join(kaggle['techniques'][:5])} |\n")
            if deep and deep.get("key_findings"):
                f.write(f"| DeepResearch | {len(deep['key_findings'])} key findings |\n")
            f.write("\n")

        # 성능 비교 (가능한 경우)
        best_model = model_data.get("best_estimator") or model_data.get("best_model", "N/A")
        if metrics:
            f.write("### Our Model Performance\n\n")
            f.write(f"**Best Model:** {best_model}\n\n")
            f.write("| Metric | Score |\n")
            f.write("|--------|-------|\n")
            for k, v in metrics.items():
                if isinstance(v, float):
                    f.write(f"| {k} | {v:.4f} |\n")
                else:
                    f.write(f"| {k} | {v} |\n")
            f.write("\n")

        if recommended:
            f.write(f"**Research-recommended models:** {', '.join(recommended[:5])}\n\n")

    def _load_shap_images_base64(self) -> List[Dict[str, str]]:
        """SHAP 이미지 파일을 base64로 로드"""
        images = []
        shap_dir = os.path.join(
            settings.OUTPUTS_DIR, "shap", self.context.session_id
        )
        if not os.path.exists(shap_dir):
            return images

        for filename in sorted(os.listdir(shap_dir)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(shap_dir, filename)
                try:
                    with open(filepath, "rb") as img_f:
                        encoded = base64.b64encode(img_f.read()).decode("utf-8")
                    ext = filename.rsplit('.', 1)[-1].lower()
                    mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else 'png'}"
                    images.append({
                        "filename": filename,
                        "data_uri": f"data:{mime};base64,{encoded}",
                    })
                except Exception:
                    pass
        return images

    def _write_appendix(self, f, report_data: Dict[str, Any]):
        """Appendix 섹션 작성"""

        f.write("### Artifacts\n\n")
        f.write("- SHAP analysis plots\n")
        f.write("- Feature importance charts\n")
        f.write("- Model performance visualizations\n")
        f.write("\n")

        f.write("### Reproducibility\n\n")
        f.write("All analysis can be reproduced using the saved model and data artifacts.\n\n")

    async def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """
        HTML 리포트 생성

        Args:
            report_data: 리포트 데이터

        Returns:
            HTML 파일 경로
        """
        try:
            self.logger.info("Generating HTML report")

            output_dir = os.path.join(
                settings.OUTPUTS_DIR,
                "reports",
                self.context.session_id
            )
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(output_dir, "report.html")

            # 간단한 HTML 템플릿
            html_content = self._create_html_template(report_data)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            self.logger.info(f"HTML report saved to {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            raise

    def _create_html_template(self, report_data: Dict[str, Any]) -> str:
        """HTML 템플릿 생성 — McKinsey-quality template"""
        template = McKinseyReportTemplate(report_data)
        shap_images = self._load_shap_images_base64()
        feature_importance = self._load_feature_importance()
        return template.render(
            executive_summary=getattr(self, '_cached_executive_summary', ''),
            shap_images=shap_images,
            feature_importance=feature_importance,
        )

    def _load_feature_importance(self) -> List[Dict]:
        """feature_importance.json 로드 — 3-stage fallback"""
        sid = self.context.session_id
        paths = [
            os.path.join(settings.OUTPUTS_DIR, "models", sid, "feature_importance.json"),
            os.path.join(settings.OUTPUTS_DIR, "insights", sid, "feature_importance.json"),
            os.path.join(settings.OUTPUTS_DIR, "analysis", sid, "feature_importance.json"),
        ]
        for fi_path in paths:
            if os.path.exists(fi_path):
                try:
                    with open(fi_path, encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue

        # context.data fallback
        model_data = self.context.data.get("model_data", {})
        fi = model_data.get("feature_importance", [])
        if fi:
            return fi
        insights = self.context.data.get("insights", {})
        return insights.get("shap_summary", [])

    def _package_artifacts(self, report_data: Dict[str, Any]) -> str:
        """
        Artifacts 패키징 (ZIP)

        Args:
            report_data: 리포트 데이터

        Returns:
            ZIP 파일 경로
        """
        try:
            self.logger.info("Packaging artifacts")

            output_dir = os.path.join(
                settings.OUTPUTS_DIR,
                "reports",
                self.context.session_id
            )

            zip_file = os.path.join(output_dir, "artifacts.zip")

            # 패키징할 디렉토리들
            dirs_to_package = [
                os.path.join(settings.OUTPUTS_DIR, "shap", self.context.session_id),
                os.path.join(settings.OUTPUTS_DIR, "insights", self.context.session_id),
                os.path.join(settings.OUTPUTS_DIR, "models", self.context.session_id),
            ]

            # ZIP 생성
            import zipfile
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for dir_path in dirs_to_package:
                    if os.path.exists(dir_path):
                        for root, dirs, files in os.walk(dir_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, settings.OUTPUTS_DIR)
                                zipf.write(file_path, arcname)

            self.logger.info(f"Artifacts packaged to {zip_file}")
            return zip_file

        except Exception as e:
            self.logger.error(f"Failed to package artifacts: {e}")
            return ""

    def _save_metadata(self, report_data: Dict[str, Any]) -> str:
        """메타데이터 저장"""

        output_dir = os.path.join(
            settings.OUTPUTS_DIR,
            "reports",
            self.context.session_id
        )

        metadata_file = os.path.join(output_dir, "metadata.json")

        metadata = {
            "session_id": report_data["session_id"],
            "timestamp": report_data["timestamp"],
            "problem_type": report_data.get("problem_definition", {}).get("problem_type"),
            "model": report_data.get("model_data", {}).get("best_estimator")
            or report_data.get("model_data", {}).get("best_model"),
            "metrics": report_data.get("model_data", {}).get("metrics", {}),
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_file}")
        return metadata_file

