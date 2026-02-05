"""Reporting Agent - 종합 리포트 생성"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import shutil
from pathlib import Path
import json

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
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
                f.write(summary)
                f.write("\n\n")

                # 2. Problem Definition
                f.write("## 2. Problem Definition\n\n")
                self._write_problem_definition(f, report_data.get("problem_definition", {}))

                # 3. Research Findings
                f.write("## 3. Prior Research\n\n")
                self._write_research_findings(f, report_data.get("research_results", {}))

                # 4. Data Analysis
                f.write("## 4. Data Analysis\n\n")
                self._write_data_analysis(f, report_data)

                # 5. Modeling
                f.write("## 5. Modeling\n\n")
                self._write_modeling_section(f, report_data.get("model_data", {}))

                # 6. Model Insights
                f.write("## 6. Model Insights\n\n")
                self._write_insights_section(f, report_data.get("insights", {}))

                # 7. Recommendations
                f.write("## 7. Recommendations\n\n")
                self._write_recommendations(f, report_data)

                # 8. Appendix
                f.write("## 8. Appendix\n\n")
                self._write_appendix(f, report_data)

            self.logger.info(f"Markdown report saved to {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"Failed to generate Markdown report: {e}")
            raise

    async def _generate_executive_summary(self, report_data: Dict[str, Any]) -> str:
        """Executive Summary 생성 (LLM 사용)"""

        try:
            # 주요 정보 추출
            problem_def = report_data.get("problem_definition", {})
            model_data = report_data.get("model_data", {})
            insights = report_data.get("insights", {})

            problem_type = problem_def.get("problem_type", "N/A")
            goal = problem_def.get("analysis_goal") or problem_def.get("goal", "N/A")
            metrics = model_data.get("metrics", {})
            key_findings = insights.get("key_findings", [])

            prompt = f"""다음 데이터 분석 프로젝트의 Executive Summary를 작성하세요.

**Problem Type:** {problem_type}
**Goal:** {goal}

**Model Performance:**
{json.dumps(metrics, indent=2)}

**Key Findings:**
{chr(10).join([f"- {f}" for f in key_findings[:5]])}

2-3 문단으로 다음을 포함하여 작성하세요:
1. 프로젝트 목표 및 접근 방법
2. 주요 결과 및 성능
3. 핵심 인사이트

간결하고 임원에게 보고하는 형식으로 작성하세요.
"""

            response = await self.generate(prompt, max_tokens=500)
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
        """HTML 템플릿 생성"""

        problem_def = report_data.get("problem_definition", {})
        model_data = report_data.get("model_data", {})
        insights = report_data.get("insights", {})

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Report - {report_data['session_id']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 5px;
        }}
        .metric-label {{
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .insight {{
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 10px 0;
        }}
        .warning {{
            background-color: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 10px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Data Analysis Report</h1>
        <p><strong>Session ID:</strong> {report_data['session_id']}</p>
        <p><strong>Generated:</strong> {report_data['timestamp']}</p>

        <h2>Problem Definition</h2>
        <p><strong>Type:</strong> {problem_def.get('problem_type', 'N/A')}</p>
        <p><strong>Goal:</strong> {problem_def.get('analysis_goal') or problem_def.get('goal', 'N/A')}</p>

        <h2>Model Performance</h2>
        <div class="metrics">
"""

        # Metrics
        metrics = model_data.get("metrics", {})
        for key, value in metrics.items():
            if isinstance(value, float):
                html += f"""
            <div class="metric">
                <div class="metric-label">{key}</div>
                <div class="metric-value">{value:.4f}</div>
            </div>
"""

        html += """
        </div>

        <h2>Key Insights</h2>
"""

        # Insights
        key_findings = insights.get("key_findings", [])
        for finding in key_findings:
            html += f'        <div class="insight">✓ {finding}</div>\n'

        html += """
        <h2>Recommendations</h2>
"""

        # Recommendations
        recommendations = insights.get("recommendations", [])
        for rec in recommendations:
            html += f'        <div class="warning">⚠ {rec}</div>\n'

        html += """
    </div>
</body>
</html>
"""

        return html

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

