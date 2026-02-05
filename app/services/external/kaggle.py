"""Kaggle API 클라이언트"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os
import asyncio
from pathlib import Path
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


@dataclass
class CompetitionInfo:
    """Competition 정보"""
    id: str
    title: str
    description: str
    url: str
    deadline: Optional[str] = None
    category: Optional[str] = None
    reward: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class KernelInfo:
    """Kernel (노트북) 정보"""
    kernel_id: str
    title: str
    author: str
    url: str
    votes: int
    medal: Optional[str] = None
    language: Optional[str] = None
    output: Optional[str] = None


@dataclass
class KaggleInsight:
    """Kaggle 인사이트"""
    competition: CompetitionInfo
    top_kernels: List[KernelInfo]
    techniques: List[str]
    recommendations: List[str]


class KaggleClient:
    """Kaggle API 클라이언트"""

    def __init__(self, username: str, key: str):
        """
        Args:
            username: Kaggle 사용자명
            key: Kaggle API 키
        """
        self.username = username
        self.key = key

        # Kaggle API 인증 설정 (env 또는 kaggle.json 사용)
        prev_username = os.environ.get('KAGGLE_USERNAME')
        prev_key = os.environ.get('KAGGLE_KEY')
        if username:
            os.environ['KAGGLE_USERNAME'] = username
        if key:
            os.environ['KAGGLE_KEY'] = key

        # 지연 import로 패키지 초기화 부작용 방지
        from kaggle.api.kaggle_api_extended import KaggleApi
        self.api = KaggleApi()
        self.api.authenticate()
        self._restore_env(prev_username, prev_key)

    @staticmethod
    def _restore_env(prev_username: str | None, prev_key: str | None) -> None:
        if prev_username is None:
            os.environ.pop('KAGGLE_USERNAME', None)
        else:
            os.environ['KAGGLE_USERNAME'] = prev_username
        if prev_key is None:
            os.environ.pop('KAGGLE_KEY', None)
        else:
            os.environ['KAGGLE_KEY'] = prev_key

    @staticmethod
    def _sanitize_output_dir(output_dir: str) -> str:
        base_dir = (Path(settings.OUTPUTS_DIR) / "research" / "kernels").resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        candidate = (base_dir / Path(output_dir).name).resolve()
        candidate.relative_to(base_dir)
        return str(candidate)

    async def search_competitions(
        self,
        query: str,
        category: str = "all",
        limit: int = 5
    ) -> List[CompetitionInfo]:
        """
        Competition 검색

        Args:
            query: 검색 쿼리
            category: 카테고리 (all, featured, research, playground, etc.)
            limit: 최대 결과 개수

        Returns:
            Competition 정보 리스트
        """
        try:
            logger.info("Searching Kaggle competitions", query=query, limit=limit)

            # Kaggle API는 동기 방식이므로 직접 호출
            competitions_list = await asyncio.wait_for(
                asyncio.to_thread(self.api.competitions_list, search=query, category=category),
                timeout=settings.LLM_TIMEOUT_SECONDS
            )

            competitions = []
            for comp in competitions_list[:limit]:
                competition = CompetitionInfo(
                    id=comp.ref,
                    title=comp.title,
                    description=comp.description or "",
                    url=f"https://www.kaggle.com/c/{comp.ref}",
                    deadline=str(comp.deadline) if comp.deadline else None,
                    category=comp.category,
                    reward=comp.reward,
                    tags=comp.tags if hasattr(comp, 'tags') else None,
                )
                competitions.append(competition)

            logger.info(f"Found {len(competitions)} competitions")
            return competitions

        except Exception as e:
            logger.error(f"Error searching competitions: {e}")
            return []

    async def get_competition_kernels(
        self,
        competition_id: str,
        sort_by: str = "votes",
        limit: int = 10
    ) -> List[KernelInfo]:
        """
        Competition의 Kernel 목록 조회

        Args:
            competition_id: Competition ID
            sort_by: 정렬 기준 (votes, relevance, date)
            limit: 최대 결과 개수

        Returns:
            Kernel 정보 리스트
        """
        try:
            logger.info("Getting competition kernels", competition_id=competition_id)

            # Kaggle API로 커널 목록 조회
            kernels_list = await asyncio.wait_for(
                asyncio.to_thread(
                    self.api.kernels_list,
                    competition=competition_id,
                    sort_by=sort_by,
                    page_size=limit
                ),
                timeout=settings.LLM_TIMEOUT_SECONDS
            )

            kernels = []
            for kernel in kernels_list[:limit]:
                kernel_info = KernelInfo(
                    kernel_id=kernel.ref,
                    title=kernel.title,
                    author=kernel.author,
                    url=f"https://www.kaggle.com/{kernel.ref}",
                    votes=kernel.totalVotes if hasattr(kernel, 'totalVotes') else 0,
                    medal=kernel.medal if hasattr(kernel, 'medal') else None,
                    language=kernel.language if hasattr(kernel, 'language') else None,
                    output=None,
                )
                kernels.append(kernel_info)

            logger.info(f"Found {len(kernels)} kernels")
            return kernels

        except Exception as e:
            logger.error(f"Error getting kernels: {e}")
            return []

    async def download_kernel_output(
        self,
        kernel_ref: str,
        output_dir: str = "./outputs/research/kernels"
    ) -> Optional[str]:
        """
        Kernel 출력 다운로드

        Args:
            kernel_ref: Kernel 참조 (username/kernel-slug)
            output_dir: 출력 디렉토리

        Returns:
            다운로드된 파일 경로
        """
        try:
            logger.info("Downloading kernel output", kernel_ref=kernel_ref)

            # 디렉토리 생성
            output_dir = self._sanitize_output_dir(output_dir)
            os.makedirs(output_dir, exist_ok=True)

            # Kernel 출력 다운로드
            await asyncio.wait_for(
                asyncio.to_thread(self.api.kernels_output, kernel_ref, path=output_dir),
                timeout=settings.LLM_TIMEOUT_SECONDS
            )

            logger.info(f"Downloaded kernel output to {output_dir}")
            return output_dir

        except Exception as e:
            logger.error(f"Error downloading kernel output: {e}")
            return None

    async def analyze_competition(
        self,
        query: str,
        limit_competitions: int = 3,
        limit_kernels: int = 5
    ) -> Optional[KaggleInsight]:
        """
        Competition 분석 및 인사이트 도출

        Args:
            query: 검색 쿼리
            limit_competitions: 검색할 Competition 개수
            limit_kernels: 각 Competition당 조회할 Kernel 개수

        Returns:
            Kaggle 인사이트
        """
        try:
            logger.info("Analyzing Kaggle competition", query=query)

            # 1. Competition 검색
            competitions = await self.search_competitions(query, limit=limit_competitions)

            if not competitions:
                logger.warning("No competitions found")
                return None

            # 가장 관련성 높은 Competition 선택
            best_competition = competitions[0]

            # 2. Top Kernel 조회
            top_kernels = await self.get_competition_kernels(
                best_competition.id,
                sort_by="votes",
                limit=limit_kernels
            )

            # 3. 기법 및 권장사항 추출 (간단한 휴리스틱)
            techniques = self._extract_techniques(top_kernels)
            recommendations = self._generate_recommendations(best_competition, top_kernels)

            insight = KaggleInsight(
                competition=best_competition,
                top_kernels=top_kernels,
                techniques=techniques,
                recommendations=recommendations,
            )

            logger.info("Kaggle analysis completed")
            return insight

        except Exception as e:
            logger.error(f"Error analyzing competition: {e}")
            return None

    def _extract_techniques(self, kernels: List[KernelInfo]) -> List[str]:
        """
        Kernel 목록에서 기법 추출

        Args:
            kernels: Kernel 정보 리스트

        Returns:
            추출된 기법 리스트
        """
        techniques = []

        # Kernel 제목에서 키워드 추출
        keywords = [
            "XGBoost", "LightGBM", "CatBoost", "Random Forest",
            "Neural Network", "Deep Learning", "Ensemble",
            "Feature Engineering", "Stacking", "Blending",
            "Cross Validation", "Hyperparameter Tuning",
            "Data Augmentation", "Transfer Learning"
        ]

        for kernel in kernels:
            title_lower = kernel.title.lower()
            for keyword in keywords:
                if keyword.lower() in title_lower and keyword not in techniques:
                    techniques.append(keyword)

        return techniques[:10]  # 상위 10개

    def _generate_recommendations(
        self,
        competition: CompetitionInfo,
        kernels: List[KernelInfo]
    ) -> List[str]:
        """
        권장사항 생성

        Args:
            competition: Competition 정보
            kernels: Kernel 정보 리스트

        Returns:
            권장사항 리스트
        """
        recommendations = []

        # 1. 가장 높은 투표를 받은 Kernel 언급
        if kernels:
            top_kernel = max(kernels, key=lambda k: k.votes)
            recommendations.append(
                f"'{top_kernel.title}' by {top_kernel.author} ({top_kernel.votes} votes) 참고"
            )

        # 2. 메달 받은 Kernel 수
        medal_kernels = [k for k in kernels if k.medal]
        if medal_kernels:
            recommendations.append(
                f"{len(medal_kernels)}개의 메달 획득 Kernel 분석"
            )

        # 3. 다양한 언어 사용
        languages = set(k.language for k in kernels if k.language)
        if languages:
            recommendations.append(
                f"주요 사용 언어: {', '.join(languages)}"
            )

        # 4. Competition 특성
        if competition.category:
            recommendations.append(
                f"Competition 카테고리: {competition.category}"
            )

        return recommendations

    def extract_query_from_problem(self, problem_definition: Dict[str, Any]) -> str:
        """
        문제 정의에서 Kaggle 검색 쿼리 추출

        Args:
            problem_definition: 문제 정의 딕셔너리

        Returns:
            검색 쿼리 문자열
        """
        keywords = []

        # 문제 유형
        problem_type = problem_definition.get("problem_type", "")
        if "classification" in problem_type.lower():
            keywords.append("classification")
        elif "regression" in problem_type.lower():
            keywords.append("regression")
        elif "time series" in problem_type.lower():
            keywords.append("time series")

        # 목표
        goal = problem_definition.get("goal") or problem_definition.get("analysis_goal", "")
        if goal:
            # 간단한 키워드 추출
            goal_words = goal.split()[:2]
            keywords.extend(goal_words)

        query = " ".join(keywords) if keywords else "machine learning"
        logger.info(f"Extracted Kaggle query: {query}")
        return query
