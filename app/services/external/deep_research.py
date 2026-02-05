"""Google Gemini DeepResearch API 클라이언트"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
import time
try:
    from google import genai as genai  # google-genai (new SDK)
    GENAI_AVAILABLE = hasattr(genai, "Client")
except ImportError:
    try:
        import google.generativeai as genai  # google-generativeai (legacy SDK)
        GENAI_AVAILABLE = hasattr(genai, "Client")
    except ImportError:
        genai = None
        GENAI_AVAILABLE = False
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DeepResearchResult:
    """DeepResearch 결과"""
    query: str
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    sources: List[str]
    full_report: str
    interaction_id: Optional[str] = None


class DeepResearchClient:
    """Google Gemini DeepResearch 클라이언트"""

    def __init__(
        self,
        api_key: str,
        agent_model: str = "deep-research-pro-preview-12-2025",
        query_model: Optional[str] = None
    ):
        """
        Args:
            api_key: Google API 키
            agent_model: 사용할 DeepResearch 에이전트 모델
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai SDK is required for DeepResearch. "
                "Install with: pip install google-genai"
            )
        self.api_key = api_key
        self.agent_model = agent_model
        self.query_model = query_model or settings.GEMINI_MODEL

        # GenAI 클라이언트 초기화
        self.client = genai.Client(api_key=api_key)

    async def conduct_research(
        self,
        query: str,
        problem_definition: Optional[Dict[str, Any]] = None,
        max_duration_minutes: int = 10,
        poll_interval: int = 10
    ) -> Optional[DeepResearchResult]:
        """
        포괄적 연구 수행 (DeepResearch Agent 사용)

        Args:
            query: 연구 쿼리
            problem_definition: 문제 정의 (선택)
            max_duration_minutes: 최대 연구 시간 (분)
            poll_interval: 상태 확인 간격 (초)

        Returns:
            연구 결과
        """
        try:
            logger.info("Starting DeepResearch", query=query, max_duration=max_duration_minutes)

            # 연구 프롬프트 생성
            full_query = self._create_research_prompt(query, problem_definition)

            # DeepResearch 백그라운드 작업 시작 (비동기)
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                input=full_query,
                agent=self.agent_model,
                background=True,
                store=True
            )

            interaction_id = interaction.id
            logger.info(f"DeepResearch interaction started: {interaction_id}")

            # 폴링으로 작업 완료 대기
            max_attempts = (max_duration_minutes * 60) // poll_interval
            for attempt in range(max_attempts):
                await asyncio.sleep(poll_interval)

                # 상태 확인 (비동기)
                interaction = await asyncio.to_thread(
                    self.client.interactions.get,
                    interaction_id
                )

                logger.info(f"DeepResearch status: {interaction.status}")

                if interaction.status == "completed":
                    # 결과 추출
                    output_text = interaction.outputs[-1].text if interaction.outputs else ""
                    result = self._parse_response(query, output_text)
                    result.interaction_id = interaction_id
                    logger.info("DeepResearch completed successfully")
                    return result

                elif interaction.status == "failed":
                    logger.error("DeepResearch failed")
                    return None

            # 타임아웃
            logger.warning(f"DeepResearch timed out after {max_duration_minutes} minutes")
            return None

        except Exception as e:
            logger.error(f"Error conducting research: {e}", exc_info=True)
            return None

    def _create_research_prompt(
        self,
        query: str,
        problem_definition: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        연구 프롬프트 생성

        Args:
            query: 연구 쿼리
            problem_definition: 문제 정의

        Returns:
            프롬프트 문자열
        """
        prompt = f"""You are a data science research assistant. Conduct broad, comprehensive research on the following topic:

Query: {query}
"""

        if problem_definition:
            goal = problem_definition.get("goal") or problem_definition.get("analysis_goal", "N/A")
            target = problem_definition.get("target_variable") or problem_definition.get("target_column", "N/A")
            prompt += f"""
Problem Context:
- Problem Type: {problem_definition.get('problem_type', 'N/A')}
- Goal: {goal}
- Target Variable: {target}
- Evaluation Metric: {problem_definition.get('evaluation_metric', 'N/A')}
"""

        prompt += """
Please provide a comprehensive research report including:

1. **Summary** (2-3 paragraphs)
   - Overview of the problem domain
   - Current state of the art
   - Key challenges

2. **Key Findings** (5-7 bullet points)
   - Most effective techniques
   - Important features/patterns
   - Common pitfalls to avoid

3. **Recommendations** (3-5 actionable items)
   - Specific algorithms/models to try
   - Feature engineering approaches
   - Hyperparameter tuning strategies
   - Evaluation approaches

4. **Sources** (if available)
   - Reference papers or articles
   - Kaggle competitions
   - GitHub repositories

5. **Coverage Notes**
   - Include alternate keywords/synonyms used during research
   - Mention any gaps or areas with limited evidence

Format your response as follows:

## Summary
[Your summary here]

## Key Findings
- [Finding 1]
- [Finding 2]
...

## Recommendations
- [Recommendation 1]
- [Recommendation 2]
...

## Sources
- [Source 1]
- [Source 2]
...
"""

        return prompt

    def _parse_response(self, query: str, response_text: str) -> DeepResearchResult:
        """
        응답 파싱

        Args:
            query: 연구 쿼리
            response_text: Gemini 응답 텍스트

        Returns:
            구조화된 연구 결과
        """
        # 섹션 추출
        sections = self._extract_sections(response_text)

        summary = sections.get("summary", "")
        key_findings = self._extract_list_items(sections.get("key_findings", ""))
        recommendations = self._extract_list_items(sections.get("recommendations", ""))
        sources = self._extract_list_items(sections.get("sources", ""))

        return DeepResearchResult(
            query=query,
            summary=summary,
            key_findings=key_findings,
            recommendations=recommendations,
            sources=sources,
            full_report=response_text,
        )

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """
        텍스트에서 섹션 추출

        Args:
            text: 전체 텍스트

        Returns:
            섹션 딕셔너리
        """
        def normalize_heading(line: str) -> Optional[str]:
            cleaned = line.strip().lstrip("#").strip().rstrip(":").lower()
            if cleaned.startswith("summary"):
                return "summary"
            if cleaned.startswith("key findings") or cleaned.startswith("findings"):
                return "key_findings"
            if cleaned.startswith("recommendations"):
                return "recommendations"
            if cleaned.startswith("sources") or cleaned.startswith("references"):
                return "sources"
            return None

        sections: Dict[str, List[str]] = {}
        current_section: Optional[str] = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current_section:
                    sections.setdefault(current_section, []).append("")
                continue

            heading = normalize_heading(line)
            if heading:
                current_section = heading
                sections.setdefault(current_section, [])
                continue

            if current_section:
                sections.setdefault(current_section, []).append(raw_line)

        return {key: "\n".join(lines).strip() for key, lines in sections.items()}

    def _extract_list_items(self, text: str) -> List[str]:
        """
        텍스트에서 리스트 아이템 추출

        Args:
            text: 리스트가 포함된 텍스트

        Returns:
            아이템 리스트
        """
        import re

        items: List[str] = []
        lines = text.split("\n")
        pattern = re.compile(r"^(\d+[\).]|[-*•–—])\s+")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if match:
                items.append(line[match.end():].strip())
                continue
            # fallback: "1 - item" 형태
            if line[0].isdigit() and " - " in line:
                items.append(line.split(" - ", 1)[1].strip())

        # 섹션에 리스트가 없으면 문장 단위로 분리 (너무 길면 상위 5개만)
        if not items and text:
            sentences = [s.strip() for s in re.split(r"[.\n]+", text) if s.strip()]
            items = sentences[:5]

        return items

    async def generate_research_query(
        self,
        problem_definition: Dict[str, Any]
    ) -> str:
        """
        문제 정의에서 연구 쿼리 생성

        Args:
            problem_definition: 문제 정의 딕셔너리

        Returns:
            연구 쿼리 문자열
        """
        try:
            # LLM으로 쿼리 생성
            goal = problem_definition.get('goal') or problem_definition.get('analysis_goal', 'N/A')
            target = problem_definition.get('target_variable') or problem_definition.get('target_column', 'N/A')
            prompt = f"""Based on the following problem definition, generate a comprehensive research query for a data science investigation:

Problem Type: {problem_definition.get('problem_type', 'N/A')}
Goal: {goal}
Target Variable: {target}
Evaluation Metric: {problem_definition.get('evaluation_metric', 'N/A')}

Generate a 1-2 sentence research query that captures the essence of this problem.
"""

            response = await asyncio.to_thread(
                self._generate_content,
                prompt,
                0.5,
                200
            )

            query = response.text.strip()
            logger.info(f"Generated research query: {query}")
            return query

        except Exception as e:
            logger.error(f"Error generating research query: {e}")
            # Fallback: 간단한 쿼리 생성
            fallback_goal = problem_definition.get('goal') or problem_definition.get('analysis_goal', 'prediction')
            return f"{problem_definition.get('problem_type', 'machine learning')} {fallback_goal}"

    async def summarize_research_results(
        self,
        papers_results: List[Dict[str, Any]],
        kaggle_results: Dict[str, Any],
        deep_research_result: DeepResearchResult
    ) -> str:
        """
        모든 연구 결과 통합 및 요약

        Args:
            papers_results: 논문 검색 결과
            kaggle_results: Kaggle 분석 결과
            deep_research_result: DeepResearch 결과

        Returns:
            통합 요약
        """
        try:
            logger.info("Summarizing all research results")

            # 통합 프롬프트 생성
            prompt = f"""You are synthesizing research results from multiple sources. Create a comprehensive summary.

## HuggingFace Papers
{self._format_papers(papers_results)}

## Kaggle Insights
{self._format_kaggle(kaggle_results)}

## Deep Research
{deep_research_result.full_report}

Based on all the above sources, provide:

1. **Executive Summary** (2-3 paragraphs)
2. **Top 5 Recommended Techniques**
3. **Top 3 Models to Try**
4. **Critical Success Factors**
5. **Potential Pitfalls**

Format the output in clear, structured Markdown.
"""

            response = await asyncio.to_thread(
                self._generate_content,
                prompt,
                0.6,
                4000
            )

            summary = response.text
            logger.info("Research summary completed")
            return summary

        except Exception as e:
            logger.error(f"Error summarizing research: {e}")
            return "Error generating summary"

    def _format_papers(self, papers: List[Dict[str, Any]]) -> str:
        """논문 결과 포맷팅"""
        if not papers:
            return "No papers found"

        formatted = []
        for paper in papers[:5]:  # 상위 5개
            formatted.append(f"- {paper.get('title', 'N/A')}: {paper.get('abstract', 'N/A')[:200]}...")

        return "\n".join(formatted)

    def _format_kaggle(self, kaggle: Dict[str, Any]) -> str:
        """Kaggle 결과 포맷팅"""
        if not kaggle:
            return "No Kaggle insights found"

        competition = kaggle.get("competition", {})
        techniques = kaggle.get("techniques", [])
        recommendations = kaggle.get("recommendations", [])

        formatted = f"""
Competition: {competition.get('title', 'N/A')}
Techniques: {', '.join(techniques) if techniques else 'N/A'}
Recommendations: {', '.join(recommendations) if recommendations else 'N/A'}
"""
        return formatted.strip()

    def _generate_content(self, prompt: str, temperature: float, max_output_tokens: int):
        """
        google-genai SDK 버전 호환 generate_content 호출
        """
        # Prefer new SDK config if available
        if hasattr(genai, "types") and hasattr(genai.types, "GenerateContentConfig"):
            config = genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )
            try:
                return self.client.models.generate_content(
                    model=self.query_model,
                    contents=prompt,
                    config=config
                )
            except TypeError:
                pass

        # Fallback to legacy GenerationConfig
        if hasattr(genai, "types") and hasattr(genai.types, "GenerationConfig"):
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )
            try:
                return self.client.models.generate_content(
                    model=self.query_model,
                    contents=prompt,
                    generation_config=config
                )
            except TypeError:
                pass

        # Last resort: call without config
        return self.client.models.generate_content(
            model=self.query_model,
            contents=prompt
        )
