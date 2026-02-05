"""Kaggle Solutions 분석 에이전트"""
from typing import Dict, Any
from datetime import datetime
import os

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.services.external.kaggle import KaggleClient, KaggleInsight
from app.config import settings
from app.utils.paths import resolve_research_path


class SolutionsAgent(BaseAgent):
    """Kaggle Competition 및 우승 솔루션 분석 에이전트"""

    def __init__(self, context: AgentContext, **kwargs):
        super().__init__(context, **kwargs)
        self.kaggle_client = KaggleClient(
            username=settings.KAGGLE_USERNAME,
            key=settings.KAGGLE_KEY
        )

    @property
    def name(self) -> str:
        return "SolutionsAgent"

    @property
    def description(self) -> str:
        return "Kaggle에서 유사 Competition과 우승 솔루션을 분석합니다"

    async def run(self) -> AgentResult:
        """
        Kaggle 솔루션 분석 실행

        Returns:
            AgentResult with Kaggle insights
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting Kaggle solutions research")

            # 1. 문제 정의에서 검색 쿼리 추출
            problem_definition = self.context.data.get("problem_definition", {})
            if not problem_definition:
                raise ValueError("Problem definition not found in context")

            query = self.kaggle_client.extract_query_from_problem(problem_definition)
            await self.emit_event("query_extracted", {"query": query})

            # 2. Competition 및 Kernel 분석
            insight = await self.kaggle_client.analyze_competition(
                query=query,
                limit_competitions=3,
                limit_kernels=5
            )

            if not insight:
                self.logger.warning("No Kaggle insights found")
                return AgentResult(
                    success=True,
                    state=AgentState.SUCCESS,
                    data={"insight": None, "summary": "No Kaggle insights found"},
                    message="No relevant Kaggle competitions found"
                )

            await self.emit_event("insights_generated", {
                "competition": insight.competition.title,
                "kernels_count": len(insight.top_kernels)
            })

            # 3. 인사이트 요약 생성 (LLM 사용)
            summary = await self._generate_summary(insight)

            # 4. 결과 저장
            output_file = resolve_research_path(self.context.session_id, "kaggle.md")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_report(insight, summary, output_file)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "insight": self._insight_to_dict(insight),
                    "summary": summary,
                    "output_file": str(output_file),
                },
                message=f"Analyzed Kaggle competition: {insight.competition.title}",
                metadata={
                    "query": query,
                    "duration": (self.end_time - self.start_time).total_seconds()
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Kaggle solutions research failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    async def _generate_summary(self, insight: KaggleInsight) -> str:
        """
        Kaggle 인사이트에서 요약 생성 (LLM 사용)

        Args:
            insight: Kaggle 인사이트

        Returns:
            요약 텍스트
        """
        try:
            # 인사이트를 텍스트로 변환
            insight_text = f"""
Competition: {insight.competition.title}
Description: {insight.competition.description[:500]}

Top Techniques: {', '.join(insight.techniques)}

Top Kernels:
"""
            for kernel in insight.top_kernels[:3]:
                insight_text += f"- {kernel.title} by {kernel.author} ({kernel.votes} votes)\n"

            insight_text += f"\nRecommendations:\n"
            for rec in insight.recommendations:
                insight_text += f"- {rec}\n"

            prompt = f"""다음은 Kaggle Competition 분석 결과입니다.

{insight_text}

이 정보를 바탕으로 다음을 제공하세요:

1. **핵심 성공 요인** (3-5개)
2. **추천 모델링 전략** (3개)
3. **피처 엔지니어링 팁** (2-3개)
4. **주의사항** (2개)

간결하고 실용적인 형태로 작성하세요.
"""

            response = await self.generate(prompt, max_tokens=1000)
            return response.content

        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return "Summary generation failed"

    def _save_report(
        self,
        insight: KaggleInsight,
        summary: str,
        output_file: str
    ):
        """
        Kaggle 리포트 저장

        Args:
            insight: Kaggle 인사이트
            summary: 요약
            output_file: 출력 파일 경로
        """
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Kaggle Solutions Research\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            f.write("## Summary\n\n")
            f.write(summary)
            f.write("\n\n")

            f.write("## Competition\n\n")
            f.write(f"**Title:** {insight.competition.title}\n\n")
            f.write(f"**URL:** {insight.competition.url}\n\n")
            f.write(f"**Description:** {insight.competition.description}\n\n")

            if insight.techniques:
                f.write("## Techniques\n\n")
                for tech in insight.techniques:
                    f.write(f"- {tech}\n")
                f.write("\n")

            f.write("## Top Kernels\n\n")
            for i, kernel in enumerate(insight.top_kernels, 1):
                f.write(f"### {i}. {kernel.title}\n\n")
                f.write(f"**Author:** {kernel.author}\n\n")
                f.write(f"**Votes:** {kernel.votes}\n\n")
                if kernel.medal:
                    f.write(f"**Medal:** {kernel.medal}\n\n")
                f.write(f"**URL:** {kernel.url}\n\n")
                f.write("---\n\n")

            if insight.recommendations:
                f.write("## Recommendations\n\n")
                for rec in insight.recommendations:
                    f.write(f"- {rec}\n")
                f.write("\n")

        self.logger.info(f"Report saved to {output_file}")

    def _insight_to_dict(self, insight: KaggleInsight) -> Dict[str, Any]:
        """인사이트를 딕셔너리로 변환"""
        return {
            "competition": {
                "id": insight.competition.id,
                "title": insight.competition.title,
                "description": insight.competition.description,
                "url": insight.competition.url,
                "deadline": insight.competition.deadline,
                "category": insight.competition.category,
                "reward": insight.competition.reward,
            },
            "top_kernels": [
                {
                    "kernel_id": k.kernel_id,
                    "title": k.title,
                    "author": k.author,
                    "url": k.url,
                    "votes": k.votes,
                    "medal": k.medal,
                }
                for k in insight.top_kernels
            ],
            "techniques": insight.techniques,
            "recommendations": insight.recommendations,
        }
