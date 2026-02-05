"""HuggingFace API 클라이언트"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx
from huggingface_hub import HfApi
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PaperInfo:
    """논문 정보"""
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    url: str
    published: Optional[str] = None
    categories: Optional[List[str]] = None
    downloads: Optional[int] = None
    likes: Optional[int] = None


class HuggingFaceClient:
    """HuggingFace Papers 검색 클라이언트"""

    def __init__(self, token: str):
        """
        Args:
            token: HuggingFace API 토큰
        """
        self.token = token
        self.api = HfApi(token=token)
        self.base_url = "https://huggingface.co"
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        sort: str = "downloads"
    ) -> List[PaperInfo]:
        """
        논문 검색

        Args:
            query: 검색 쿼리
            limit: 최대 결과 개수
            sort: 정렬 기준 (downloads, likes, updated)

        Returns:
            논문 정보 리스트
        """
        try:
            logger.info("Searching HuggingFace papers", query=query, limit=limit)

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                data = await self._search_papers_hf(client, query, limit, sort)
                if data is None:
                    raise httpx.HTTPStatusError(
                        "HuggingFace papers endpoint not found",
                        request=httpx.Request("GET", f"{self.base_url}/api/papers/search"),
                        response=httpx.Response(status_code=404)
                    )

            papers = []
            items = self._extract_papers_items(data)
            for item in items[:limit]:
                paper_id = item.get("id") or item.get("_id") or item.get("paperId") or ""
                title = item.get("title") or item.get("paperTitle") or ""
                authors = item.get("authors") or item.get("author") or []
                abstract = item.get("summary") or item.get("abstract") or item.get("paperAbstract") or ""
                url = item.get("url") or (
                    f"https://huggingface.co/papers/{paper_id}" if paper_id else ""
                )
                paper = PaperInfo(
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=url,
                    published=item.get("publishedAt") or item.get("published"),
                    categories=item.get("tags") or item.get("categories"),
                    downloads=item.get("downloads"),
                    likes=item.get("likes"),
                )
                papers.append(paper)

            logger.info(f"Found {len(papers)} papers")
            return papers

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching papers: {e}")
            # Fallback: ArXiv 검색 시도
            return await self._search_arxiv_fallback(query, limit)
        except Exception as e:
            logger.error(f"Error searching papers: {e}")
            raise

    async def _search_arxiv_fallback(
        self,
        query: str,
        limit: int = 10
    ) -> List[PaperInfo]:
        """
        ArXiv API를 통한 대체 검색 (HuggingFace API 실패 시)

        Args:
            query: 검색 쿼리
            limit: 최대 결과 개수

        Returns:
            논문 정보 리스트
        """
        try:
            logger.info("Using ArXiv fallback", query=query)

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={
                        "search_query": f"all:{query}",
                        "start": 0,
                        "max_results": limit,
                        "sortBy": "relevance",
                        "sortOrder": "descending",
                    },
                )
                response.raise_for_status()

            # ArXiv XML 파싱
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            papers = []
            for entry in root.findall("atom:entry", ns)[:limit]:
                paper_id = entry.find("atom:id", ns).text.split("/")[-1]
                title = entry.find("atom:title", ns).text.strip()
                abstract = entry.find("atom:summary", ns).text.strip()
                authors = [
                    author.find("atom:name", ns).text
                    for author in entry.findall("atom:author", ns)
                ]
                published = entry.find("atom:published", ns).text
                url = entry.find("atom:id", ns).text

                paper = PaperInfo(
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=url,
                    published=published,
                    categories=None,
                    downloads=None,
                    likes=None,
                )
                papers.append(paper)

            logger.info(f"Found {len(papers)} papers from ArXiv")
            return papers

        except Exception as e:
            logger.error(f"ArXiv fallback failed: {e}")
            return []

    async def _search_papers_hf(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int,
        sort: str
    ) -> Optional[Dict[str, Any]]:
        """
        HuggingFace Papers API 검색 (엔드포인트 호환)
        - /api/papers/search?q=...
        - /api/papers?search=... (legacy)
        """
        endpoints = [
            (f"{self.base_url}/api/papers/search", "q"),
            (f"{self.base_url}/api/papers", "search"),
        ]

        for url, query_param in endpoints:
            response = await client.get(
                url,
                params={
                    query_param: query,
                    "limit": limit,
                    "sort": sort,
                },
                headers=self.headers,
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            return response.json()

        return None

    @staticmethod
    def _extract_papers_items(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("papers", "items", "results"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []

    async def get_paper_details(self, paper_id: str) -> Optional[PaperInfo]:
        """
        논문 상세 정보 조회

        Args:
            paper_id: 논문 ID

        Returns:
            논문 정보
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/papers/{paper_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

            paper = PaperInfo(
                paper_id=data.get("id", ""),
                title=data.get("title", ""),
                authors=data.get("authors", []),
                abstract=data.get("summary", ""),
                url=f"https://huggingface.co/papers/{paper_id}",
                published=data.get("publishedAt"),
                categories=data.get("tags", []),
                downloads=data.get("downloads"),
                likes=data.get("likes"),
            )

            return paper

        except Exception as e:
            logger.error(f"Error getting paper details: {e}")
            return None

    def extract_keywords(self, problem_definition: Dict[str, Any]) -> str:
        """
        문제 정의에서 검색 키워드 추출

        Args:
            problem_definition: 문제 정의 딕셔너리

        Returns:
            검색 쿼리 문자열
        """
        keywords = []

        # 문제 유형
        problem_type = problem_definition.get("problem_type", "")
        if problem_type:
            keywords.append(problem_type)

        # 타겟 변수
        target = problem_definition.get("target_variable") or problem_definition.get("target_column", "")
        if target:
            keywords.append(target)

        # 도메인/목표
        goal = problem_definition.get("goal") or problem_definition.get("analysis_goal", "")
        if goal:
            # 간단한 키워드 추출 (첫 3단어)
            goal_words = goal.split()[:3]
            keywords.extend(goal_words)

        # 데이터셋 특성
        if "data_characteristics" in problem_definition:
            chars = problem_definition["data_characteristics"]
            if "domain" in chars:
                keywords.append(chars["domain"])

        query = " ".join(keywords)
        logger.info(f"Extracted keywords: {query}")
        return query
