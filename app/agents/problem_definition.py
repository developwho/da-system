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
        """시스템 프롬프트 생성 — few-shot 예시 포함"""
        return """당신은 데이터 분석 전문가입니다.
사용자의 데이터를 분석하여 문제를 정의하는 것이 목표입니다.

다음 정보를 추출해주세요:
1. 분석 목표 (Analysis Goal)
2. 타겟 변수 (Target Variable)
3. 문제 유형 (Problem Type: binary_classification, multiclass_classification, regression, time_series)
4. 평가 지표 (Evaluation Metric: accuracy, f1, roc_auc, rmse, mae 등)
5. 제약사항 (Constraints)

**추론 과정:** 왜 이 타겟이 적합한지, 왜 이 메트릭이 적절한지 단계적으로 설명하세요.

**예시 1 — 고객 이탈 데이터:**
입력: customer_id, tenure, monthly_charges, total_charges, contract, churn
분석:
- churn 컬럼은 이진 값(Yes/No)으로 타겟 후보
- 고객 이탈 예측은 binary_classification
- 이탈 고객은 보통 소수 → 불균형 가능 → f1 또는 roc_auc 적합
출력: {"analysis_goal": "고객 이탈 예측", "target_column": "churn", "problem_type": "binary_classification", "evaluation_metric": "f1", "constraints": [], "reasoning": "churn은 이진 분류 타겟으로 불균형이 예상되어 F1이 적절"}

**예시 2 — 주택 가격 데이터:**
입력: area, bedrooms, bathrooms, location, price
분석:
- price는 연속형 수치 → 회귀 문제
- 이상치 가능 → rmse 적합
출력: {"analysis_goal": "주택 가격 예측", "target_column": "price", "problem_type": "regression", "evaluation_metric": "rmse", "constraints": [], "reasoning": "price는 연속형 값으로 회귀 문제, RMSE가 표준 메트릭"}

**예시 3 — 의료 진단 데이터:**
입력: age, bmi, blood_pressure, glucose, diagnosis
분석:
- diagnosis는 범주형(정상/당뇨/전당뇨) → multiclass_classification
- 의료 도메인 → 재현율 중요 → f1_macro 적합
출력: {"analysis_goal": "질병 진단 예측", "target_column": "diagnosis", "problem_type": "multiclass_classification", "evaluation_metric": "f1_macro", "constraints": ["해석 가능한 모델 선호"], "reasoning": "의료 데이터에서 각 클래스별 균형 평가가 중요하여 F1 Macro 적용"}

응답은 반드시 JSON 형식으로 작성해주세요:
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
        """사용자 프롬프트 생성 — 전체 컬럼 + 핵심 통계 포함"""
        overview = profile.get("overview", profile.get("basic_info", {}))
        variables = profile.get("variables", profile.get("column_types", {}))
        correlations = profile.get("correlations", {})

        # 컬럼 상세 정보 (최대 50개)
        col_details = []
        for col, info in list(variables.items())[:50]:
            var_type = info.get("variable_type") or info.get("type")
            stats = info.get("statistics", {})
            missing_pct = info.get("missing_pct", 0)

            if var_type == "numeric" or str(info.get("type", "")).startswith(("int", "float")):
                summary = f"  {col} (수치, min={stats.get('min', '?')}, max={stats.get('max', '?')}, mean={stats.get('mean', '?')}"
                if missing_pct > 0:
                    summary += f", 결측 {missing_pct:.1f}%"
                summary += ")"
            elif var_type in ("categorical", "object"):
                cardinality = info.get("cardinality", info.get("unique_count", "?"))
                summary = f"  {col} (범주, 고유값 {cardinality}개"
                if missing_pct > 0:
                    summary += f", 결측 {missing_pct:.1f}%"
                summary += ")"
            else:
                summary = f"  {col} (타입: {var_type or info.get('type', '?')})"

            col_details.append(summary)

        col_text = "\n".join(col_details)

        # 고상관 쌍
        high_corr = correlations.get("high_correlations", [])
        corr_text = ""
        if high_corr:
            pairs = [f"  {p['var1']} ↔ {p['var2']} (r={p['correlation']:.2f})" for p in high_corr[:5]]
            corr_text = f"\n고상관 컬럼 쌍:\n" + "\n".join(pairs)

        # 도메인 정보 (DataIntelligence 결과)
        data_intel = self.context.data.get("data_intelligence", {})
        domain_info = data_intel.get("domain", {})
        domain_text = ""
        if domain_info.get("domain") and domain_info["domain"] != "general":
            domain_text = f"\n감지된 도메인: {domain_info['domain']} (신뢰도 {domain_info.get('confidence', 0):.0%})"

        # 불균형 정보
        imbalance = data_intel.get("class_imbalance", {})
        imbalance_text = ""
        if imbalance.get("detected"):
            imbalance_text = f"\n클래스 불균형 감지: {imbalance.get('severity')} (비율 {imbalance.get('ratio', '?')}:1, 소수 클래스 {imbalance.get('minority_pct', '?')}%)"

        problem_type_name = problem_type.get("problem_type") or problem_type.get("task_type", "unknown")
        confidence_raw = problem_type.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        prompt = f"""데이터셋 정보:
- 행 수: {overview.get('n_observations', overview.get('rows', 0)):,}
- 열 수: {overview.get('n_variables', overview.get('columns', 0))}

전체 컬럼:
{col_text}
{corr_text}{domain_text}{imbalance_text}

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

        # 타겟 검증 + 폴백
        llm_target = response_json.get("target_column", recommended_target)
        if not self._validate_target(llm_target, problem_type_name):
            # DataIntelligence 점수 기반 폴백
            data_intel = self.context.data.get("data_intelligence", {})
            candidates = data_intel.get("target_candidates", [])
            for candidate in candidates:
                if self._validate_target(candidate["column"], problem_type_name):
                    self.logger.info("target_fallback_to_candidate",
                                   original=llm_target, fallback=candidate["column"])
                    llm_target = candidate["column"]
                    break
            else:
                # 모든 후보 실패 시 기존 로직
                if recommended_target:
                    llm_target = recommended_target

        # 기본값 설정
        problem_definition = {
            "analysis_goal": response_json.get("analysis_goal", "데이터 분석 및 예측 모델 구축"),
            "target_column": llm_target,
            "problem_type": problem_type_name,
            "evaluation_metric": response_json.get("evaluation_metric", self._get_default_metric(problem_type_name)),
            "constraints": constraints,
            "reasoning": response_json.get("reasoning", ""),
            "confidence": problem_type.get("confidence", 0.0)
        }

        return problem_definition

    def _get_default_metric(self, problem_type: str) -> str:
        """문제 유형별 기본 평가 지표 — 데이터 불균형 반영"""
        # DataIntelligence 불균형 정보 활용
        data_intel = self.context.data.get("data_intelligence", {})
        imbalance = data_intel.get("class_imbalance", {})

        if problem_type == "binary_classification":
            if imbalance.get("ratio", 1) > 5:
                return "f1"  # 불균형 시 F1 선호
            return "roc_auc"

        metrics = {
            "multiclass_classification": "f1_macro",
            "regression": "rmse",
            "time_series": "mae",
            "timeseries": "mae"
        }
        return metrics.get(problem_type, "accuracy")

    def _validate_target(self, target_column: str, problem_type: str) -> bool:
        """LLM이 반환한 target_column 유효성 검증"""
        if not target_column or not hasattr(self, "data"):
            return False

        if target_column not in self.data.columns:
            return False

        col = self.data[target_column]

        # ID 컬럼 검사 (>90% unique)
        if col.nunique() > len(col) * 0.9:
            self.logger.warning("target_validation_failed_id_column", column=target_column)
            return False

        # 분류 문제인데 고유값 너무 많은 경우
        if "classification" in problem_type and col.nunique() > 100:
            self.logger.warning("target_validation_failed_high_cardinality",
                              column=target_column, nunique=col.nunique())
            return False

        return True

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
