"""Google Gemini DeepResearch 에이전트"""
from typing import Dict, Any
from datetime import datetime
import os

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.services.external.deep_research import DeepResearchClient, DeepResearchResult
from app.config import settings
from app.utils.paths import resolve_research_path


class DeepResearchAgent(BaseAgent):
    """Google Gemini DeepResearch 에이전트"""

    def __init__(self, context: AgentContext, **kwargs):
        super().__init__(context, **kwargs)
        self.deep_research_client = DeepResearchClient(
            api_key=settings.GOOGLE_API_KEY,
            agent_model="deep-research-pro-preview-12-2025"
        )

    @property
    def name(self) -> str:
        return "DeepResearchAgent"

    @property
    def description(self) -> str:
        return "Google Gemini DeepResearch를 사용하여 포괄적인 조사를 수행합니다"

    async def run(self) -> AgentResult:
        """
        DeepResearch 실행

        Returns:
            AgentResult with research data
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting DeepResearch")

            # 1. 문제 정의 가져오기
            problem_definition = self.context.data.get("problem_definition", {})
            if not problem_definition:
                raise ValueError("Problem definition not found in context")

            # 2. 연구 쿼리 생성
            query = await self.deep_research_client.generate_research_query(problem_definition)
            await self.emit_event("query_generated", {"query": query})

            # 3. DeepResearch 수행 (최대 10분)
            await self.emit_event("research_started", {"query": query})

            research_result = await self.deep_research_client.conduct_research(
                query=query,
                problem_definition=problem_definition,
                max_duration_minutes=10,
                poll_interval=15  # 15초마다 상태 확인
            )

            if not research_result:
                self.logger.warning("DeepResearch returned no results")
                return AgentResult(
                    success=True,
                    state=AgentState.SUCCESS,
                    data={"result": None, "summary": "DeepResearch failed"},
                    message="DeepResearch did not complete successfully"
                )

            await self.emit_event("research_completed", {
                "interaction_id": research_result.interaction_id,
                "findings_count": len(research_result.key_findings)
            })

            # 4. 결과 저장
            output_file = resolve_research_path(self.context.session_id, "deep_research.md")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_report(research_result, output_file)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "result": self._result_to_dict(research_result),
                    "output_file": str(output_file),
                },
                message="DeepResearch completed successfully",
                metadata={
                    "query": query,
                    "interaction_id": research_result.interaction_id,
                    "duration": (self.end_time - self.start_time).total_seconds()
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"DeepResearch failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    def _save_report(
        self,
        result: DeepResearchResult,
        output_file: str
    ):
        """
        DeepResearch 리포트 저장

        Args:
            result: DeepResearch 결과
            output_file: 출력 파일 경로
        """
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Google Gemini DeepResearch Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Query:** {result.query}\n\n")
            if result.interaction_id:
                f.write(f"**Interaction ID:** {result.interaction_id}\n\n")
            f.write("---\n\n")

            f.write("## Summary\n\n")
            f.write(result.summary)
            f.write("\n\n")

            if result.key_findings:
                f.write("## Key Findings\n\n")
                for finding in result.key_findings:
                    f.write(f"- {finding}\n")
                f.write("\n")

            if result.recommendations:
                f.write("## Recommendations\n\n")
                for rec in result.recommendations:
                    f.write(f"- {rec}\n")
                f.write("\n")

            if result.sources:
                f.write("## Sources\n\n")
                for source in result.sources:
                    f.write(f"- {source}\n")
                f.write("\n")

            f.write("## Full Report\n\n")
            f.write(result.full_report)
            f.write("\n")

        self.logger.info(f"Report saved to {output_file}")

    def _result_to_dict(self, result: DeepResearchResult) -> Dict[str, Any]:
        """결과를 딕셔너리로 변환"""
        return {
            "query": result.query,
            "summary": result.summary,
            "key_findings": result.key_findings,
            "recommendations": result.recommendations,
            "sources": result.sources,
            "full_report": result.full_report,
            "interaction_id": result.interaction_id,
        }
