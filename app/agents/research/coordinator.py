"""Research Coordinator 에이전트"""
from typing import Dict, Any, List
from datetime import datetime
import asyncio
import os

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.agents.contracts import normalize_research_results
from app.agents.research.papers_agent import PapersAgent
from app.agents.research.solutions_agent import SolutionsAgent
from app.agents.research.deep_research_agent import DeepResearchAgent
from app.services.external.deep_research import DeepResearchClient
from app.config import settings
from app.utils.paths import resolve_research_path


class ResearchCoordinator(BaseAgent):
    """
    Research Coordinator 에이전트

    3개의 연구 에이전트를 병렬로 실행하고 결과를 통합합니다:
    - PapersAgent: HuggingFace/ArXiv 논문 검색
    - SolutionsAgent: Kaggle 우승 솔루션 분석
    - DeepResearchAgent: Google Gemini DeepResearch
    """

    def __init__(self, context: AgentContext, **kwargs):
        super().__init__(context, **kwargs)
        self.deep_research_client = DeepResearchClient(
            api_key=settings.GOOGLE_API_KEY
        )

    @property
    def name(self) -> str:
        return "ResearchCoordinator"

    @property
    def description(self) -> str:
        return "선행 연구를 조율하고 통합합니다 (논문, Kaggle, DeepResearch)"

    async def run(self) -> AgentResult:
        """
        Research Coordinator 실행

        Returns:
            AgentResult with integrated research data
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting Research Coordinator")

            # 1. 3개의 에이전트를 병렬로 실행
            await self.emit_event("parallel_research_started", {
                "agents": ["PapersAgent", "SolutionsAgent", "DeepResearchAgent"]
            })

            papers_agent = PapersAgent(self.context, llm_provider=self.llm_provider)
            solutions_agent = SolutionsAgent(self.context, llm_provider=self.llm_provider)
            deep_research_agent = DeepResearchAgent(self.context, llm_provider=self.llm_provider)

            # 병렬 실행
            results = await asyncio.gather(
                papers_agent.execute(),
                solutions_agent.execute(),
                deep_research_agent.execute(),
                return_exceptions=True  # 에러 발생 시에도 계속 진행
            )

            papers_result, solutions_result, deep_research_result = results

            # 2. 결과 검증
            self._log_agent_results([
                ("PapersAgent", papers_result),
                ("SolutionsAgent", solutions_result),
                ("DeepResearchAgent", deep_research_result),
            ])

            # 3. 결과 통합
            integrated_data = await self._integrate_results(
                papers_result,
                solutions_result,
                deep_research_result
            )

            # 4. 통합 요약 생성
            summary = await self._generate_integrated_summary(integrated_data)

            # 5. 통합 리포트 저장
            summary_file = resolve_research_path(self.context.session_id, "summary.md")
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_summary_report(integrated_data, summary, summary_file)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            raw_data = {
                "integrated_data": integrated_data,
                "summary": summary,
                "summary_file": str(summary_file),
                "papers_result": papers_result.data if isinstance(papers_result, AgentResult) else {},
                "solutions_result": solutions_result.data if isinstance(solutions_result, AgentResult) else {},
                "deep_research_result": deep_research_result.data if isinstance(deep_research_result, AgentResult) else {},
            }
            normalized = normalize_research_results(raw_data)

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data=normalized,
                message="Research coordination completed successfully",
                metadata={
                    "duration": (self.end_time - self.start_time).total_seconds(),
                    "agents_count": 3,
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Research coordination failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    def _log_agent_results(self, results: List[tuple]):
        """에이전트 결과 로깅"""
        for agent_name, result in results:
            if isinstance(result, Exception):
                self.logger.error(f"{agent_name} failed with exception", error=str(result))
            elif isinstance(result, AgentResult):
                if result.success:
                    self.logger.info(f"{agent_name} completed successfully")
                else:
                    self.logger.warning(f"{agent_name} failed", error=result.error)
            else:
                self.logger.warning(f"{agent_name} returned unexpected result type")

    async def _integrate_results(
        self,
        papers_result: AgentResult,
        solutions_result: AgentResult,
        deep_research_result: AgentResult
    ) -> Dict[str, Any]:
        """
        3개 에이전트 결과 통합

        Args:
            papers_result: Papers 에이전트 결과
            solutions_result: Solutions 에이전트 결과
            deep_research_result: DeepResearch 에이전트 결과

        Returns:
            통합된 데이터
        """
        integrated = {
            "papers": None,
            "kaggle_solutions": None,
            "deep_research": None,
            "techniques": [],
            "recommended_models": [],
            "key_insights": [],
        }

        # Papers 데이터
        if isinstance(papers_result, AgentResult) and papers_result.success:
            integrated["papers"] = papers_result.data.get("papers", [])

        # Kaggle 데이터
        if isinstance(solutions_result, AgentResult) and solutions_result.success:
            kaggle_data = solutions_result.data.get("insight", {})
            integrated["kaggle_solutions"] = kaggle_data
            if kaggle_data:
                integrated["techniques"].extend(kaggle_data.get("techniques", []))

        # DeepResearch 데이터
        if isinstance(deep_research_result, AgentResult) and deep_research_result.success:
            deep_data = deep_research_result.data.get("result", {})
            integrated["deep_research"] = deep_data
            if deep_data:
                integrated["key_insights"].extend(deep_data.get("key_findings", []))
                integrated["recommended_models"].extend(deep_data.get("recommendations", []))

        # 중복 제거
        integrated["techniques"] = list(set(integrated["techniques"]))
        integrated["recommended_models"] = list(set(integrated["recommended_models"]))

        return integrated

    async def _generate_integrated_summary(self, integrated_data: Dict[str, Any]) -> str:
        """
        통합 요약 생성 (LLM 사용) — 도메인 컨텍스트 + 합의 기법 추출

        Args:
            integrated_data: 통합 데이터

        Returns:
            요약 텍스트
        """
        try:
            # 도메인 컨텍스트
            problem_def = self.context.data.get("problem_definition", {})
            domain_info = self.context.data.get("data_intelligence", {}).get("domain", {})
            domain_ctx = ""
            if domain_info and domain_info.get("domain", "general") != "general":
                domain_ctx = f"\n**분석 도메인:** {domain_info['domain']}"
            goal = problem_def.get("analysis_goal") or problem_def.get("goal", "")
            if goal:
                domain_ctx += f"\n**분석 목표:** {goal}"

            # 각 소스의 정보 추출
            papers_count = len(integrated_data.get("papers", []) or [])
            kaggle_data = integrated_data.get("kaggle_solutions") or integrated_data.get("kaggle")
            deep_research_data = integrated_data.get("deep_research")

            prompt = f"""다음은 3개의 선행 연구 소스에서 수집한 정보입니다.
{domain_ctx}

**HuggingFace Papers:**
- {papers_count}개의 관련 논문 발견

**Kaggle Solutions:**
{self._format_kaggle_summary(kaggle_data)}

**Google DeepResearch:**
{self._format_deep_research_summary(deep_research_data)}

**추출된 기법:** {', '.join(integrated_data.get('techniques', [])[:10])}

이 정보들을 종합하여 다음을 JSON 형식으로 제공하세요:

{{
  "executive_summary": "3-4문장 요약",
  "top_techniques": ["기법1", "기법2", ...],
  "recommended_models": ["모델1", "모델2", "모델3"],
  "success_factors": ["요인1", "요인2", "요인3"],
  "warnings": ["주의1", "주의2"],
  "source_relevance": {{
    "papers": 0-10 점수,
    "kaggle": 0-10 점수,
    "deep_research": 0-10 점수
  }}
}}

참고:
- 여러 소스에서 공통으로 언급된 기법에 높은 우선순위 부여
- recommended_models는 FLAML에서 사용 가능한 모델명 (xgboost, lightgbm, catboost, random forest 등)으로 반환
- 각 소스의 관련성 점수(0-10)도 포함
"""

            response = await self.generate(prompt, max_tokens=1500, temperature=0.4)
            content = response.content

            # JSON 파싱 시도 → recommended_models 추출
            import re
            try:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    import json
                    parsed = json.loads(json_match.group())
                    # recommended_models를 integrated_data에 반영
                    if parsed.get("recommended_models"):
                        integrated_data["recommended_models"] = list(set(
                            integrated_data.get("recommended_models", []) +
                            parsed["recommended_models"]
                        ))
            except (json.JSONDecodeError, AttributeError):
                pass

            return content

        except Exception as e:
            self.logger.error(f"Failed to generate integrated summary: {e}")
            return "통합 요약 생성 실패"

    def _format_kaggle_summary(self, kaggle_data: Dict[str, Any]) -> str:
        """Kaggle 데이터 요약 포맷팅"""
        if not kaggle_data:
            return "데이터 없음"

        competition = kaggle_data.get("competition", {})
        techniques = kaggle_data.get("techniques", [])
        return f"Competition: {competition.get('title', 'N/A')}, Techniques: {', '.join(techniques[:5])}"

    def _format_deep_research_summary(self, deep_data: Dict[str, Any]) -> str:
        """DeepResearch 데이터 요약 포맷팅"""
        if not deep_data:
            return "데이터 없음"

        summary = deep_data.get("summary", "N/A")
        findings_count = len(deep_data.get("key_findings", []))
        return f"Summary: {summary[:200]}..., Key Findings: {findings_count}개"

    def _save_summary_report(
        self,
        integrated_data: Dict[str, Any],
        summary: str,
        output_file: str
    ):
        """
        통합 요약 리포트 저장

        Args:
            integrated_data: 통합 데이터
            summary: 요약 텍스트
            output_file: 출력 파일 경로
        """
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Research Summary\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Session ID:** {self.context.session_id}\n\n")
            f.write("---\n\n")

            f.write("## Integrated Summary\n\n")
            f.write(summary)
            f.write("\n\n")

            f.write("## Sources\n\n")
            f.write(f"- **HuggingFace Papers:** {len(integrated_data.get('papers', []))} papers\n")

            kaggle_data = integrated_data.get("kaggle_solutions") or integrated_data.get("kaggle")
            if kaggle_data and kaggle_data.get("competition"):
                f.write(f"- **Kaggle Competition:** {kaggle_data['competition'].get('title', 'N/A')}\n")

            deep_data = integrated_data.get("deep_research")
            if deep_data and deep_data.get("interaction_id"):
                f.write(f"- **DeepResearch Interaction:** {deep_data['interaction_id']}\n")

            f.write("\n")

            if integrated_data.get("techniques"):
                f.write("## Identified Techniques\n\n")
                for tech in integrated_data["techniques"][:15]:
                    f.write(f"- {tech}\n")
                f.write("\n")

            if integrated_data.get("key_insights"):
                f.write("## Key Insights\n\n")
                for insight in integrated_data["key_insights"][:10]:
                    f.write(f"- {insight}\n")
                f.write("\n")

            f.write("---\n\n")
            f.write("## Individual Reports\n\n")
            f.write("- [HuggingFace Papers](./papers.md)\n")
            f.write("- [Kaggle Solutions](./kaggle.md)\n")
            f.write("- [DeepResearch Report](./deep_research.md)\n")

        self.logger.info(f"Summary report saved to {output_file}")
