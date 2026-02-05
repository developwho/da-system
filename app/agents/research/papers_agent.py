"""HuggingFace Papers 검색 에이전트"""
from typing import Dict, Any, List
from datetime import datetime
import os

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.services.external.huggingface import HuggingFaceClient, PaperInfo
from app.config import settings
from app.utils.paths import resolve_research_path


class PapersAgent(BaseAgent):
    """HuggingFace/ArXiv 논문 검색 에이전트"""

    def __init__(self, context: AgentContext, **kwargs):
        super().__init__(context, **kwargs)
        self.hf_client = HuggingFaceClient(token=settings.HUGGINGFACE_TOKEN)

    @property
    def name(self) -> str:
        return "PapersAgent"

    @property
    def description(self) -> str:
        return "HuggingFace 및 ArXiv에서 관련 논문을 검색하고 분석합니다"

    async def run(self) -> AgentResult:
        """
        논문 검색 및 분석 실행

        Returns:
            AgentResult with papers data
        """
        try:
            self.state = AgentState.RUNNING
            self.start_time = datetime.now()
            self.logger.info("Starting papers research")

            # 1. 문제 정의에서 검색 쿼리 추출
            problem_definition = self.context.data.get("problem_definition", {})
            if not problem_definition:
                raise ValueError("Problem definition not found in context")

            query = self.hf_client.extract_keywords(problem_definition)
            await self.emit_event("query_extracted", {"query": query})

            # 2. 논문 검색
            papers = await self.hf_client.search_papers(
                query=query,
                limit=10,
                sort="downloads"
            )

            if not papers:
                self.logger.warning("No papers found")
                return AgentResult(
                    success=True,
                    state=AgentState.SUCCESS,
                    data={"papers": [], "summary": "No papers found"},
                    message="No relevant papers found"
                )

            await self.emit_event("papers_found", {"count": len(papers)})

            # 3. 논문 요약 생성 (LLM 사용)
            summary = await self._generate_summary(papers)

            # 4. 결과 저장
            output_file = resolve_research_path(self.context.session_id, "papers.md")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_report(papers, summary, output_file)

            self.end_time = datetime.now()
            self.state = AgentState.SUCCESS

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "papers": [self._paper_to_dict(p) for p in papers],
                    "summary": summary,
                    "output_file": str(output_file),
                },
                message=f"Found {len(papers)} relevant papers",
                metadata={
                    "query": query,
                    "duration": (self.end_time - self.start_time).total_seconds()
                }
            )

        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Papers research failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    async def _generate_summary(self, papers: List[PaperInfo]) -> str:
        """
        논문 목록에서 요약 생성 (LLM 사용)

        Args:
            papers: 논문 정보 리스트

        Returns:
            요약 텍스트
        """
        try:
            # 논문 정보를 텍스트로 변환
            papers_text = "\n\n".join([
                f"Title: {p.title}\n"
                f"Authors: {', '.join(p.authors)}\n"
                f"Abstract: {p.abstract[:500]}..."
                for p in papers[:5]  # 상위 5개만
            ])

            prompt = f"""다음은 데이터 분석 문제와 관련된 논문 목록입니다.

{papers_text}

이 논문들을 분석하여 다음을 제공하세요:

1. **핵심 기법 요약** (3-5개)
2. **추천 모델/알고리즘** (3개)
3. **주의사항 및 베스트 프랙티스** (2-3개)

간결하고 실용적인 형태로 작성하세요.
"""

            response = await self.generate(prompt, max_tokens=1000)
            return response.content

        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return "Summary generation failed"

    def _save_report(
        self,
        papers: List[PaperInfo],
        summary: str,
        output_file: str
    ):
        """
        논문 리포트 저장

        Args:
            papers: 논문 정보 리스트
            summary: 요약
            output_file: 출력 파일 경로
        """
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# HuggingFace Papers Research\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            f.write("## Summary\n\n")
            f.write(summary)
            f.write("\n\n")

            f.write("## Papers\n\n")
            for i, paper in enumerate(papers, 1):
                f.write(f"### {i}. {paper.title}\n\n")
                f.write(f"**Authors:** {', '.join(paper.authors)}\n\n")
                f.write(f"**URL:** {paper.url}\n\n")
                if paper.published:
                    f.write(f"**Published:** {paper.published}\n\n")
                f.write(f"**Abstract:**\n{paper.abstract}\n\n")
                f.write("---\n\n")

        self.logger.info(f"Report saved to {output_file}")

    def _paper_to_dict(self, paper: PaperInfo) -> Dict[str, Any]:
        """논문 정보를 딕셔너리로 변환"""
        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "url": paper.url,
            "published": paper.published,
            "categories": paper.categories,
            "downloads": paper.downloads,
            "likes": paper.likes,
        }
