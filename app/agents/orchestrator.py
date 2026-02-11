"""Orchestrator Agent - 최상위 조율 에이전트"""
from typing import Optional, Dict, Any
from enum import Enum

from .base import BaseAgent, AgentContext, AgentResult, AgentState
from .contracts import (
    normalize_problem_definition,
    normalize_research_results,
    normalize_modeling_result,
    normalize_insights_result,
)
from app.services.llm import LLMProvider
from app.storage.session_store import get_session_store


class WorkflowState(str, Enum):
    """워크플로우 상태"""
    IDLE = "idle"
    PROBLEM_DEFINITION = "problem_definition"
    RESEARCH = "research"
    MODELING = "modeling"
    INSIGHT = "insight"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent

    전체 워크플로우를 조율하는 최상위 에이전트
    상태 머신 기반으로 각 단계별 에이전트를 순차적으로 실행
    """

    def __init__(
        self,
        context: AgentContext,
        llm_provider: Optional[LLMProvider] = None
    ):
        super().__init__(context, llm_provider)
        self.workflow_state = WorkflowState.IDLE

    @property
    def name(self) -> str:
        return "OrchestratorAgent"

    @property
    def description(self) -> str:
        return "전체 분석 워크플로우를 조율하는 최상위 에이전트"

    async def run(self) -> AgentResult:
        """
        워크플로우 실행

        상태 머신:
        IDLE → PROBLEM_DEFINITION → RESEARCH → MODELING → INSIGHT → REPORTING → COMPLETED
        """
        self.logger.info("orchestrator_started", session_id=self.context.session_id)

        try:
            start_state = self.workflow_state
            if start_state == WorkflowState.IDLE:
                start_state = WorkflowState.PROBLEM_DEFINITION
            return await self._run_from_state(start_state)
        except Exception as e:
            self.workflow_state = WorkflowState.FAILED
            self._persist_workflow_state()
            self.logger.error("orchestrator_failed", error=str(e))
            return self._create_failure_result(str(e))

    async def _run_problem_definition(self) -> AgentResult:
        """문제 정의 단계 실행"""
        self.logger.info("phase_started", phase="problem_definition")
        await self.emit_event(event_type="phase_change", data={"phase": "problem_definition"})

        try:
            from .problem_definition import ProblemDefinitionAgent

            agent = ProblemDefinitionAgent(self.context, self.llm_provider)
            result = await agent.execute()

            if not result.success:
                self.logger.error("problem_definition_failed", error=result.error)
                return result

            self.logger.info("phase_completed", phase="problem_definition",
                           problem_type=result.data.get("problem_type"))
            return result

        except Exception as e:
            self.logger.error("problem_definition_exception", error=str(e), exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=f"Problem definition failed: {str(e)}"
            )

    async def _run_research(self) -> AgentResult:
        """선행 연구 단계 실행 (병렬)"""
        self.logger.info("phase_started", phase="research")
        await self.emit_event(event_type="phase_change", data={"phase": "research"})

        try:
            from .research.coordinator import ResearchCoordinator

            agent = ResearchCoordinator(self.context, llm_provider=self.llm_provider)
            result = await agent.execute()

            if not result.success:
                self.logger.warning("research_failed", error=result.error)
                # Research 실패는 치명적이지 않으므로 빈 데이터로 계속 진행
                return AgentResult(
                    success=True,
                    state=AgentState.SUCCESS,
                    data={
                        "papers": [],
                        "kaggle_solutions": [],
                        "deep_research": {},
                        "summary": "Research phase skipped due to errors"
                    },
                    message="Research phase completed with warnings"
                )

            self.logger.info("phase_completed", phase="research")
            return result

        except Exception as e:
            self.logger.error("research_exception", error=str(e), exc_info=True)
            # Research 실패는 치명적이지 않으므로 경고만 하고 계속 진행
            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={
                    "papers": [],
                    "kaggle_solutions": [],
                    "deep_research": {},
                    "summary": f"Research phase skipped: {str(e)}"
                },
                message="Research phase completed with warnings"
            )

    async def _run_modeling(self) -> AgentResult:
        """모델링 단계 실행"""
        self.logger.info("phase_started", phase="modeling")
        await self.emit_event(event_type="phase_change", data={"phase": "modeling"})

        try:
            from .modeling import ModelingAgent

            agent = ModelingAgent(self.context, self.llm_provider)
            result = await agent.execute()

            if not result.success:
                self.logger.error("modeling_failed", error=result.error)
                return result

            self.logger.info("phase_completed", phase="modeling",
                           best_estimator=result.data.get("best_estimator"),
                           metrics=result.data.get("metrics"))
            return result

        except Exception as e:
            self.logger.error("modeling_exception", error=str(e), exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=f"Modeling failed: {str(e)}"
            )

    async def _run_insight(self) -> AgentResult:
        """인사이트 도출 단계 실행"""
        self.logger.info("phase_started", phase="insight")
        await self.emit_event(event_type="phase_change", data={"phase": "insight"})

        try:
            from .insight import InsightAgent

            agent = InsightAgent(self.context, self.llm_provider)
            result = await agent.execute()

            if not result.success:
                self.logger.error("insight_failed", error=result.error)
                return result

            self.logger.info("phase_completed", phase="insight",
                           insights_count=len(result.data.get("insights", [])))
            return result

        except Exception as e:
            self.logger.error("insight_exception", error=str(e), exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=f"Insight generation failed: {str(e)}"
            )

    async def _run_reporting(self) -> AgentResult:
        """리포트 생성 단계 실행"""
        self.logger.info("phase_started", phase="reporting")
        await self.emit_event(event_type="phase_change", data={"phase": "reporting"})

        try:
            from .reporting import ReportingAgent

            agent = ReportingAgent(self.context, self.llm_provider)
            result = await agent.execute()

            if not result.success:
                self.logger.error("reporting_failed", error=result.error)
                return result

            self.logger.info("phase_completed", phase="reporting",
                           markdown_report=result.data.get("markdown_report"),
                           html_report=result.data.get("html_report"))
            return result

        except Exception as e:
            self.logger.error("reporting_exception", error=str(e), exc_info=True)
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=f"Report generation failed: {str(e)}"
            )

    async def _run_from_state(self, start_state: WorkflowState) -> AgentResult:
        """현재 상태에서 워크플로우 이어서 실행"""
        steps = [
            (WorkflowState.PROBLEM_DEFINITION, self._run_problem_definition, "problem_definition"),
            (WorkflowState.RESEARCH, self._run_research, "research"),
            (WorkflowState.MODELING, self._run_modeling, "modeling"),
            (WorkflowState.INSIGHT, self._run_insight, "insight"),
            (WorkflowState.REPORTING, self._run_reporting, "report"),
        ]

        try:
            start_index = next(
                index for index, (state, _, _) in enumerate(steps) if state == start_state
            )
        except StopIteration:
            start_index = 0

        results = {
            "problem_definition": self.get_context("problem_definition"),
            "research": self.get_context("research"),
            "modeling": self.get_context("modeling"),
            "insight": self.get_context("insight"),
            "report": self.get_context("report"),
        }

        for state, step_fn, result_key in steps[start_index:]:
            self.workflow_state = state
            self._persist_workflow_state()

            result = await step_fn()
            if not result.success:
                return self._create_failure_result(f"{state.value} failed: {result.error}")

            normalized_result = result.data

            # 다음 단계를 위한 데이터 정규화/매핑
            if result_key == "problem_definition":
                normalized_result = normalize_problem_definition(result.data)
                if "file_id" not in normalized_result:
                    normalized_result["file_id"] = self.context.data.get("file_id")
                if "file_path" not in normalized_result:
                    normalized_result["file_path"] = self.context.data.get("file_path")
                # DataIntelligence 전파 — 후속 에이전트(modeling, insight, reporting)가 접근 가능
                if "data_intelligence" not in normalized_result:
                    di = self.context.data.get("data_intelligence")
                    if di:
                        normalized_result["data_intelligence"] = di
                        self.update_context("data_intelligence", di)
                else:
                    self.update_context("data_intelligence", normalized_result["data_intelligence"])
                self.update_context("problem_definition", normalized_result)
            elif result_key == "research":
                normalized_result = normalize_research_results(result.data)
                self.update_context("research_results", normalized_result)
            elif result_key == "modeling":
                model_data = normalize_modeling_result(result.data)
                normalized_result = dict(result.data)
                normalized_result["model_data"] = model_data
                self.update_context("model_data", model_data)
            elif result_key == "insight":
                normalized_result = normalize_insights_result(result.data)
                self.update_context("insights", normalized_result)

            # 결과 데이터 저장
            self.update_context(result_key, normalized_result)
            results[result_key] = normalized_result

            self._persist_context()

        self.workflow_state = WorkflowState.COMPLETED
        self._persist_workflow_state()
        self.logger.info("orchestrator_completed", session_id=self.context.session_id)

        return AgentResult(
            success=True,
            state=AgentState.SUCCESS,
            data={
                "workflow_state": self.workflow_state,
                "problem_definition": results.get("problem_definition"),
                "research": results.get("research"),
                "modeling": results.get("modeling"),
                "insight": results.get("insight"),
                "report": results.get("report"),
            },
            message="전체 분석 워크플로우 완료"
        )

    def _create_failure_result(self, error_message: str) -> AgentResult:
        """실패 결과 생성"""
        return AgentResult(
            success=False,
            state=AgentState.FAILED,
            data={"workflow_state": self.workflow_state},
            error=error_message
        )

    async def pause(self):
        """워크플로우 일시 정지"""
        self.logger.info("orchestrator_paused", workflow_state=self.workflow_state)
        self.state = AgentState.PAUSED

    async def resume(self):
        """워크플로우 재개"""
        self.logger.info("orchestrator_resumed", workflow_state=self.workflow_state)
        self.state = AgentState.RUNNING
        if self.workflow_state == WorkflowState.COMPLETED:
            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data={"workflow_state": self.workflow_state},
                message="워크플로우가 이미 완료되었습니다"
            )
        if self.workflow_state in [WorkflowState.FAILED, WorkflowState.IDLE]:
            return await self._run_from_state(WorkflowState.PROBLEM_DEFINITION)
        return await self._run_from_state(self.workflow_state)

    async def get_status(self) -> Dict[str, Any]:
        """현재 상태 조회"""
        return {
            "workflow_state": self.workflow_state,
            "agent_state": self.state,
            "session_id": self.context.session_id,
            "history": self.context.history,
        }

    def _persist_workflow_state(self) -> None:
        """세션 스토어에 워크플로우 상태 저장"""
        try:
            session_store = get_session_store()
            session_store.update_context(
                self.context.session_id,
                {"workflow_state": self.workflow_state.value}
            )
        except Exception as exc:
            self.logger.warning("workflow_state_persist_failed", error=str(exc))

    # Keys in model_data that are non-serializable (DataFrame, ndarray, model objects)
    _NON_SERIALIZABLE_KEYS = frozenset({
        "model", "X_train", "X_test", "y_train", "y_test",
        "predictions", "feature_names",
    })

    def _persist_context(self) -> None:
        """현재 컨텍스트를 세션 스토어에 저장 (비직렬화 객체 재귀 제거)"""
        try:
            data_copy = dict(self.context.data)
            # model_data, modeling 키에서 비직렬화 객체 재귀 제거
            for key in ("model_data", "modeling"):
                if key in data_copy and isinstance(data_copy[key], dict):
                    data_copy[key] = self._strip_non_serializable(data_copy[key])
            session_store = get_session_store()
            session_store.update_context(
                self.context.session_id,
                data_copy
            )
        except Exception as exc:
            self.logger.warning("context_persist_failed", error=str(exc))

    @classmethod
    def _strip_non_serializable(cls, d: dict) -> dict:
        """딕셔너리에서 비직렬화 객체를 재귀적으로 제거"""
        cleaned = {}
        for k, v in d.items():
            if k in cls._NON_SERIALIZABLE_KEYS:
                continue
            if isinstance(v, dict):
                cleaned[k] = cls._strip_non_serializable(v)
            elif isinstance(v, (str, int, float, bool, type(None))):
                cleaned[k] = v
            elif isinstance(v, list):
                cleaned[k] = cls._strip_list(v)
            # numpy/pandas/model objects are silently skipped
        return cleaned

    @classmethod
    def _strip_list(cls, lst: list) -> list:
        """리스트에서 직렬화 가능한 항목만 유지"""
        result = []
        for item in lst:
            if isinstance(item, (str, int, float, bool, type(None))):
                result.append(item)
            elif isinstance(item, dict):
                result.append(cls._strip_non_serializable(item))
            elif isinstance(item, list):
                result.append(cls._strip_list(item))
        return result
