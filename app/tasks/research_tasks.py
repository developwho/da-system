"""Research 관련 Celery 태스크"""
from celery import chord
import asyncio
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.agents.base import AgentContext
from app.agents.research import ResearchCoordinator
from app.storage.session_store import SessionStore
from app.utils.logger import get_logger

logger = get_logger(__name__)

def _run_async(coro):
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        if loop:
            try:
                loop.close()
            finally:
                asyncio.set_event_loop(None)


@celery_app.task(name="coordinate_research", bind=True)
def coordinate_research_task(self, session_id: str, problem_definition: dict):
    """
    Research Coordinator 실행 (병렬 실행)

    Args:
        session_id: 세션 ID
        problem_definition: 문제 정의 딕셔너리

    Returns:
        연구 결과 딕셔너리
    """
    try:
        logger.info(f"Starting research coordination for session {session_id}")

        # 진행률 업데이트
        self.update_state(state="PROGRESS", meta={"status": "Starting research", "progress": 0})

        # AgentContext 생성
        context = AgentContext(
            session_id=session_id,
            data={"problem_definition": problem_definition}
        )

        # ResearchCoordinator 실행 (비동기 → 동기로 실행)
        coordinator = ResearchCoordinator(context)

        result = _run_async(coordinator.run())

        # 진행률 업데이트
        self.update_state(state="PROGRESS", meta={"status": "Research completed", "progress": 100})

        # 결과 반환
        if result.success:
            logger.info(f"Research coordination completed for session {session_id}")
            return {
                "success": True,
                "data": result.data,
                "message": result.message,
                "metadata": result.metadata,
            }
        else:
            logger.error(f"Research coordination failed: {result.error}")
            return {
                "success": False,
                "error": result.error,
            }

    except Exception as e:
        logger.error(f"Research coordination task failed: {e}", exc_info=True)
        self.update_state(state="FAILURE", meta={"error": str(e)})
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task(name="run_papers_research", bind=True)
def run_papers_research_task(self, session_id: str, problem_definition: dict):
    """
    Papers Agent 실행

    Args:
        session_id: 세션 ID
        problem_definition: 문제 정의

    Returns:
        논문 검색 결과
    """
    try:
        from app.agents.research import PapersAgent

        logger.info(f"Starting papers research for session {session_id}")
        self.update_state(state="PROGRESS", meta={"status": "Searching papers", "progress": 0})

        context = AgentContext(
            session_id=session_id,
            data={"problem_definition": problem_definition}
        )

        agent = PapersAgent(context)

        result = _run_async(agent.run())

        self.update_state(state="PROGRESS", meta={"status": "Papers search completed", "progress": 100})

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }

    except Exception as e:
        logger.error(f"Papers research task failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="run_kaggle_research", bind=True)
def run_kaggle_research_task(self, session_id: str, problem_definition: dict):
    """
    Solutions Agent 실행

    Args:
        session_id: 세션 ID
        problem_definition: 문제 정의

    Returns:
        Kaggle 분석 결과
    """
    try:
        from app.agents.research import SolutionsAgent

        logger.info(f"Starting Kaggle research for session {session_id}")
        self.update_state(state="PROGRESS", meta={"status": "Analyzing Kaggle", "progress": 0})

        context = AgentContext(
            session_id=session_id,
            data={"problem_definition": problem_definition}
        )

        agent = SolutionsAgent(context)

        result = _run_async(agent.run())

        self.update_state(state="PROGRESS", meta={"status": "Kaggle analysis completed", "progress": 100})

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }

    except Exception as e:
        logger.error(f"Kaggle research task failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="run_deep_research", bind=True)
def run_deep_research_task(self, session_id: str, problem_definition: dict):
    """
    DeepResearch Agent 실행

    Args:
        session_id: 세션 ID
        problem_definition: 문제 정의

    Returns:
        DeepResearch 결과
    """
    try:
        from app.agents.research import DeepResearchAgent

        logger.info(f"Starting DeepResearch for session {session_id}")
        self.update_state(state="PROGRESS", meta={"status": "Running DeepResearch", "progress": 0})

        context = AgentContext(
            session_id=session_id,
            data={"problem_definition": problem_definition}
        )

        agent = DeepResearchAgent(context)

        result = _run_async(agent.run())

        self.update_state(state="PROGRESS", meta={"status": "DeepResearch completed", "progress": 100})

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }

    except Exception as e:
        logger.error(f"DeepResearch task failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="parallel_research")
def parallel_research_task(session_id: str, problem_definition: dict):
    """
    병렬 연구 실행 (Celery chord 사용)

    Args:
        session_id: 세션 ID
        problem_definition: 문제 정의

    Returns:
        통합 연구 결과
    """
    try:
        logger.info(f"Starting parallel research for session {session_id}")

        # 3개의 태스크를 병렬로 실행
        job = chord([
            run_papers_research_task.s(session_id, problem_definition),
            run_kaggle_research_task.s(session_id, problem_definition),
            run_deep_research_task.s(session_id, problem_definition),
        ])(aggregate_research_results.s(session_id))

        return {
            "task_id": job.id,
            "status": "parallel_tasks_started",
        }

    except Exception as e:
        logger.error(f"Parallel research task failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="aggregate_research_results")
def aggregate_research_results(results: list, session_id: str):
    """
    연구 결과 통합 (Celery chord callback)

    Args:
        results: 각 태스크의 결과 리스트
        session_id: 세션 ID

    Returns:
        통합된 결과
    """
    try:
        logger.info(f"Aggregating research results for session {session_id}")

        if not results or len(results) != 3:
            raise ValueError("Research results are incomplete")

        papers_result, kaggle_result, deep_research_result = results

        # SessionStore에 결과 저장
        session_store = SessionStore()

        integrated_data = {
            "papers": papers_result.get("data") if papers_result.get("success") else None,
            "kaggle": kaggle_result.get("data") if kaggle_result.get("success") else None,
            "deep_research": deep_research_result.get("data") if deep_research_result.get("success") else None,
            "aggregated_at": datetime.now().isoformat(),
        }

        # 세션에 저장
        session_store.update_session(
            session_id,
            {"research_results": integrated_data}
        )

        logger.info(f"Research results aggregated for session {session_id}")

        return {
            "success": True,
            "data": integrated_data,
        }

    except Exception as e:
        logger.error(f"Result aggregation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
