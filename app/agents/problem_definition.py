"""Problem Definition Agent - 문제 정의 에이전트"""
from typing import Optional, Dict, Any, List
import pandas as pd

from .base import BaseAgent, AgentContext, AgentResult, AgentState
from app.services.llm import LLMMessage, LLMProvider
from app.core.data_pipeline.profiler import DataProfiler
from app.core.data_pipeline.type_detector import TypeDetector


class ProblemDefinitionAgent(BaseAgent):
    """
    Problem Definition Agent

    대화형 인터페이스로 사용자와 소통하며 분석 문제를 정의합니다:
    - 분석 목표 파악
    - 타겟 변수 식별
    - 문제 유형 자동 감지 (분류/회귀/시계열)
    - 평가 지표 결정
    - 제약사항 수집
    """

    def __init__(
        self,
        context: AgentContext,
        llm_provider: Optional[LLMProvider] = None
    ):
        super().__init__(context, llm_provider)
        self.profiler = DataProfiler()
        self.type_detector = TypeDetector()

    @property
    def name(self) -> str:
        return "ProblemDefinitionAgent"

    @property
    def description(self) -> str:
        return "대화형 문제 정의 및 데이터 분석 에이전트"

    async def run(self) -> AgentResult:
        """문제 정의 실행"""
        self.logger.info("problem_definition_started")

        try:
            # 0. Context에서 데이터 가져오기
            dataframe = self.context.data.get("dataframe")

            # DataFrame이 없으면 file_path나 file_id로부터 로드
            if dataframe is None:
                file_path = self.context.data.get("file_path")
                file_id = self.context.data.get("file_id")

                if file_path:
                    from app.core.data_pipeline.loader import DataLoader
                    self.logger.info("loading_dataframe_from_file", file_path=file_path)
                    dataframe, _ = DataLoader.load_file(file_path)
                elif file_id:
                    from app.storage.file_manager import FileManager
                    from app.core.data_pipeline.loader import DataLoader
                    self.logger.info("loading_dataframe_from_file_id", file_id=file_id)
                    file_path = FileManager.get_file_path(file_id)
                    dataframe, _ = DataLoader.load_file(file_path)
                else:
                    raise ValueError(
                        "No data found in context. "
                        "Please provide 'dataframe', 'file_path', or 'file_id' in context."
                    )

            if not isinstance(dataframe, pd.DataFrame):
                raise ValueError(f"Expected pd.DataFrame, got {type(dataframe).__name__}")

            self.data = dataframe
            self.logger.info("dataframe_loaded", shape=dataframe.shape)

            # 1. 데이터 프로파일링 (항상 실행 - downstream 에이전트에 필요)
            profile = await self._profile_data()
            self.logger.debug("profile_keys", keys=list(profile.keys()))

            # Check for user-defined problem (Q&A bypass)
            user_defined = self.context.data.get("user_defined_problem")
            if user_defined:
                self.logger.info("using_user_defined_problem", target=user_defined.get("target_column"))
                problem_definition = {
                    "analysis_goal": user_defined.get("analysis_goal", "데이터 분석 및 예측 모델 구축"),
                    "target_column": user_defined.get("target_column"),
                    "problem_type": user_defined.get("problem_type", "binary_classification"),
                    "evaluation_metric": user_defined.get("evaluation_metric", "accuracy"),
                    "constraints": user_defined.get("constraints", []),
                    "reasoning": "사용자가 직접 분석 설정을 지정했습니다.",
                    "confidence": 1.0,
                }
            else:
                # 2. 문제 유형 자동 감지
                problem_type = await self._detect_problem_type(profile)

                # 3. LLM을 통한 문제 정의 대화
                problem_definition = await self._define_problem_with_llm(profile, problem_type)

            # 4. 결과 컨텍스트에 저장
            self.update_context("data_profile", profile)
            self.update_context("problem_type", problem_definition["problem_type"])
            self.update_context("target_column", problem_definition["target_column"])
            self.update_context("evaluation_metric", problem_definition["evaluation_metric"])
            self.update_context("constraints", problem_definition.get("constraints", []))

            self.logger.info("problem_definition_completed", problem_type=problem_definition["problem_type"])

            return AgentResult(
                success=True,
                state=AgentState.SUCCESS,
                data=problem_definition,
                message="문제 정의 완료"
            )

        except Exception as e:
            self.logger.error("problem_definition_failed", error=str(e))
            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    async def _profile_data(self) -> Dict[str, Any]:
        """데이터 프로파일링"""
        self.logger.info("data_profiling_started")

        profile = self.profiler.profile(self.data)

        # 프로파일러 반환 형식 처리
        overview = profile.get("overview", profile.get("basic_info", {}))
        rows = overview.get("n_observations", overview.get("rows", 0))
        columns = overview.get("n_variables", overview.get("columns", 0))

        self.logger.info(
            "data_profiling_completed",
            rows=rows,
            columns=columns
        )

        return profile

    async def _detect_problem_type(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """문제 유형 자동 감지"""
        self.logger.info("problem_type_detection_started")

        detection_result = self.type_detector.detect(self.data)
        # 호환성: task_type -> problem_type
        if "problem_type" not in detection_result and "task_type" in detection_result:
            detection_result["problem_type"] = detection_result["task_type"]

        self.logger.info(
            "problem_type_detected",
            problem_type=detection_result.get("problem_type"),
            confidence=detection_result.get("confidence", 0.0)
        )

        return detection_result

    async def _define_problem_with_llm(
        self,
        profile: Dict[str, Any],
        problem_type: Dict[str, Any]
    ) -> Dict[str, Any]:
        """LLM을 통한 문제 정의"""
        self.logger.info("llm_problem_definition_started")

        # LLM 프롬프트 생성
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(profile, problem_type)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        # LLM 호출
        response = await self.llm_generate(messages, temperature=0.3, max_tokens=2000)
        self.logger.debug(
            "llm_raw_response_preview",
            length=len(response.content or ""),
            preview=(response.content or "")[:500]
        )

        # 응답 파싱
        problem_definition = self._parse_llm_response(response.content, problem_type)

        self.logger.info("llm_problem_definition_completed")

        return problem_definition

    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 데이터 분석 전문가입니다.
사용자의 데이터를 분석하여 문제를 정의하는 것이 목표입니다.

다음 정보를 추출해주세요:
1. 분석 목표 (Analysis Goal)
2. 타겟 변수 (Target Variable)
3. 문제 유형 (Problem Type: classification, regression, time_series)
4. 평가 지표 (Evaluation Metric: accuracy, f1, roc_auc, rmse, mae 등)
5. 제약사항 (Constraints: 시간, 리소스, 성능 요구사항 등)

응답은 다음 JSON 형식으로 작성해주세요:
{
    "analysis_goal": "...",
    "target_column": "...",
    "problem_type": "...",
    "evaluation_metric": "...",
    "constraints": ["...", "..."],
    "reasoning": "..."
}
"""

    def _create_user_prompt(
        self,
        profile: Dict[str, Any],
        problem_type: Dict[str, Any]
    ) -> str:
        """사용자 프롬프트 생성"""
        # 프로파일러 반환 형식 처리 (overview, variables)
        overview = profile.get("overview", profile.get("basic_info", {}))
        variables = profile.get("variables", profile.get("column_types", {}))

        # 칼럼 정보 요약
        def is_numeric_variable(info: Dict[str, Any]) -> bool:
            var_type = info.get("variable_type") or info.get("type")
            if var_type == "numeric":
                return True
            if var_type in ["categorical", "object", "datetime"]:
                return False
            dtype_name = str(info.get("type", ""))
            return dtype_name.startswith(("int", "float", "uint"))

        def is_categorical_variable(info: Dict[str, Any]) -> bool:
            var_type = info.get("variable_type") or info.get("type")
            if var_type in ["categorical", "object"]:
                return True
            dtype_name = str(info.get("type", ""))
            return dtype_name in ["object", "category", "bool"]

        numeric_cols = [col for col, info in variables.items() if is_numeric_variable(info)]
        categorical_cols = [col for col, info in variables.items() if is_categorical_variable(info)]
        problem_type_name = problem_type.get("problem_type") or problem_type.get("task_type", "unknown")
        confidence_raw = problem_type.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        prompt = f"""데이터셋 정보:
- 행 수: {overview.get('n_observations', overview.get('rows', 0)):,}
- 열 수: {overview.get('n_variables', overview.get('columns', 0))}
- 숫자형 변수: {len(numeric_cols)}개 ({', '.join(numeric_cols[:5])}{', ...' if len(numeric_cols) > 5 else ''})
- 범주형 변수: {len(categorical_cols)}개 ({', '.join(categorical_cols[:5])}{', ...' if len(categorical_cols) > 5 else ''})

자동 감지된 문제 유형:
- 유형: {problem_type_name}
- 신뢰도: {confidence:.2%}
- 추천 타겟 변수: {problem_type.get('recommended_target', 'N/A')}

위 정보를 바탕으로 문제를 정의해주세요.
"""
        return prompt

    def _parse_llm_response(
        self,
        response_text: str,
        problem_type: Dict[str, Any]
    ) -> Dict[str, Any]:
        """LLM 응답 파싱"""
        import json
        import re

        problem_type = problem_type or {}

        # JSON 추출 시도
        try:
            # JSON 블록 찾기
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_json = json.loads(json_match.group())
            else:
                # JSON 없으면 기본값 사용
                response_json = {}
        except json.JSONDecodeError:
            response_json = {}

        if not isinstance(response_json, dict):
            response_json = {}

        problem_type_name = (
            response_json.get("problem_type")
            or problem_type.get("problem_type")
            or problem_type.get("task_type")
            or "unknown"
        )
        recommended_target = problem_type.get("recommended_target")
        if not recommended_target and hasattr(self.data, "columns"):
            if "target" in self.data.columns:
                recommended_target = "target"
            elif len(self.data.columns) > 0:
                recommended_target = self.data.columns[-1]

        constraints = response_json.get("constraints", [])
        if isinstance(constraints, str):
            constraints = [constraints]

        # 기본값 설정
        problem_definition = {
            "analysis_goal": response_json.get("analysis_goal", "데이터 분석 및 예측 모델 구축"),
            "target_column": response_json.get("target_column", recommended_target),
            "problem_type": problem_type_name,
            "evaluation_metric": response_json.get("evaluation_metric", self._get_default_metric(problem_type_name)),
            "constraints": constraints,
            "reasoning": response_json.get("reasoning", ""),
            "confidence": problem_type.get("confidence", 0.0)
        }

        return problem_definition

    def _get_default_metric(self, problem_type: str) -> str:
        """문제 유형별 기본 평가 지표"""
        metrics = {
            "binary_classification": "roc_auc",
            "multiclass_classification": "f1_macro",
            "regression": "rmse",
            "time_series": "mae",
            "timeseries": "mae"
        }
        return metrics.get(problem_type, "accuracy")

    async def ask_user(self, question: str) -> str:
        """
        사용자에게 질문 (대화형 인터페이스)

        TODO: Chat API 통해 실제 사용자 응답 받기
        현재는 placeholder
        """
        self.logger.info("asking_user", question=question)

        # 이벤트 발행 (WebSocket/SSE로 전송 가능)
        await self.emit_event(event_type="agent_question", data={
            "question": question,
            "agent": self.name
        })

        # TODO: 실제 사용자 응답 대기
        return "placeholder_answer"

    async def refine_definition(self, user_feedback: str) -> AgentResult:
        """
        사용자 피드백 기반으로 문제 정의 수정

        Args:
            user_feedback: 사용자 피드백

        Returns:
            AgentResult: 수정된 문제 정의
        """
        self.logger.info("refining_problem_definition", feedback=user_feedback)

        current_definition = {
            "target_column": self.get_context("target_column"),
            "problem_type": self.get_context("problem_type"),
            "evaluation_metric": self.get_context("evaluation_metric")
        }

        messages = [
            LLMMessage(
                role="system",
                content="사용자 피드백을 반영하여 문제 정의를 수정하세요."
            ),
            LLMMessage(
                role="user",
                content=f"""현재 정의: {current_definition}
사용자 피드백: {user_feedback}

수정된 정의를 JSON 형식으로 반환하세요."""
            )
        ]

        response = await self.llm_generate(messages, temperature=0.3)
        refined_definition = self._parse_llm_response(response.content, {})

        # 컨텍스트 업데이트
        for key, value in refined_definition.items():
            self.update_context(key, value)

        return AgentResult(
            success=True,
            state=AgentState.SUCCESS,
            data=refined_definition,
            message="문제 정의 수정 완료"
        )
