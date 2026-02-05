"""
Phase 3 테스트: 에이전트 시스템 검증
- LLM 서비스 통합
- BaseAgent 및 Orchestrator
- Problem Definition Agent
- Chat API
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.llm import llm_router, LLMMessage, LLMProvider
from app.agents import AgentContext, OrchestratorAgent, ProblemDefinitionAgent
from app.config import settings
import pandas as pd


async def test_llm_services():
    """LLM 서비스 테스트"""
    print("\n" + "="*60)
    print("1. LLM 서비스 통합 테스트")
    print("="*60)

    # 사용 가능한 제공자 확인
    available_providers = llm_router.list_available_providers()
    print(f"\n[OK] 사용 가능한 LLM 제공자: {[p.value for p in available_providers]}")

    # 간단한 텍스트 생성 테스트
    messages = [
        LLMMessage(role="system", content="You are a helpful data science assistant."),
        LLMMessage(role="user", content="What is machine learning in one sentence?")
    ]

    try:
        response = await llm_router.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=100
        )

        print(f"\n[OK] LLM 응답 성공:")
        print(f"  - 제공자: {response.provider}")
        print(f"  - 모델: {response.model}")
        print(f"  - 응답: {response.content[:100]}...")
        print(f"  - 토큰 사용: {response.usage}")

        return True

    except Exception as e:
        print(f"\n[FAIL] LLM 응답 실패: {e}")
        return False


async def test_base_agent():
    """BaseAgent 테스트"""
    print("\n" + "="*60)
    print("2. BaseAgent 클래스 테스트")
    print("="*60)

    # 테스트용 에이전트 생성
    context = AgentContext(
        session_id="test-session-001",
        user_id="test-user"
    )

    # Orchestrator Agent 생성
    orchestrator = OrchestratorAgent(context)

    print(f"\n[OK] Orchestrator Agent 생성 성공")
    print(f"  - 이름: {orchestrator.name}")
    print(f"  - 설명: {orchestrator.description}")
    print(f"  - 상태: {orchestrator.state}")

    # 상태 조회 테스트
    status = await orchestrator.get_status()
    print(f"\n[OK] 상태 조회 성공:")
    print(f"  - 워크플로우 상태: {status['workflow_state']}")
    print(f"  - 에이전트 상태: {status['agent_state']}")

    return True


async def test_problem_definition_agent():
    """Problem Definition Agent 테스트"""
    print("\n" + "="*60)
    print("3. Problem Definition Agent 테스트")
    print("="*60)

    # 테스트 데이터 생성
    test_data = pd.DataFrame({
        'feature1': range(100),
        'feature2': range(100, 200),
        'category': ['A', 'B'] * 50,
        'target': [0, 1] * 50
    })

    print(f"\n[OK] 테스트 데이터 생성: {test_data.shape}")

    # Agent 컨텍스트 생성
    context = AgentContext(
        session_id="test-pd-001",
        user_id="test-user"
    )

    # Problem Definition Agent 생성
    pd_agent = ProblemDefinitionAgent(
        context=context,
        data=test_data
    )

    print(f"\n[OK] Problem Definition Agent 생성:")
    print(f"  - 이름: {pd_agent.name}")
    print(f"  - 설명: {pd_agent.description}")

    # 에이전트 실행
    try:
        print("\n[RUNNING] 문제 정의 실행 중...")
        result = await pd_agent.execute()

        if result.success:
            print(f"\n[OK] 문제 정의 성공:")
            print(f"  - 문제 유형: {result.data.get('problem_type')}")
            print(f"  - 타겟 변수: {result.data.get('target_column')}")
            print(f"  - 평가 지표: {result.data.get('evaluation_metric')}")
            print(f"  - 신뢰도: {result.data.get('confidence', 0):.2%}")
            return True
        else:
            print(f"\n[FAIL] 문제 정의 실패: {result.error}")
            return False

    except Exception as e:
        print(f"\n[FAIL] 문제 정의 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestrator_workflow():
    """Orchestrator 워크플로우 테스트"""
    print("\n" + "="*60)
    print("4. Orchestrator 워크플로우 테스트")
    print("="*60)

    # Agent 컨텍스트 생성
    context = AgentContext(
        session_id="test-orch-001",
        user_id="test-user"
    )

    # 테스트 데이터 설정
    context.data["problem_type"] = "binary_classification"
    context.data["target_column"] = "target"
    context.data["evaluation_metric"] = "roc_auc"

    # Orchestrator 생성
    orchestrator = OrchestratorAgent(context)

    print(f"\n[OK] Orchestrator Agent 생성 완료")

    # 워크플로우 실행 (임시 구현이므로 빠르게 완료됨)
    try:
        print("\n[RUNNING] 워크플로우 실행 중...")
        result = await orchestrator.execute()

        if result.success:
            print(f"\n[OK] 워크플로우 실행 성공:")
            print(f"  - 상태: {result.data.get('workflow_state')}")
            print(f"  - 완료된 단계:")
            for phase in ['problem_definition', 'research', 'modeling', 'insight', 'report']:
                if phase in result.data:
                    print(f"    [OK] {phase}")
            return True
        else:
            print(f"\n[FAIL] 워크플로우 실행 실패: {result.error}")
            return False

    except Exception as e:
        print(f"\n[FAIL] 워크플로우 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("Phase 3: 에이전트 시스템 통합 테스트")
    print("="*60)

    # API 키 검증
    print("\nAPI Key validation:")
    api_validation = settings.validate_api_keys()
    for provider, valid in api_validation.items():
        status = "[OK]" if valid else "[X]"
        print(f"  {status} {provider}: {'configured' if valid else 'not configured'}")

    # LLM API가 하나라도 설정되어 있는지 확인
    if not any([api_validation['openai'], api_validation['anthropic'], api_validation['google']]):
        print("\n[WARN] 경고: LLM API 키가 설정되지 않았습니다.")
        print("일부 테스트가 실패할 수 있습니다.")

    # 테스트 실행
    results = []

    # 1. LLM 서비스 테스트
    if any([api_validation['openai'], api_validation['anthropic'], api_validation['google']]):
        result = await test_llm_services()
        results.append(("LLM 서비스", result))
    else:
        print("\n[SKIP] LLM 서비스 테스트 건너뜀 (API 키 없음)")
        results.append(("LLM 서비스", None))

    # 2. BaseAgent 테스트
    result = await test_base_agent()
    results.append(("BaseAgent", result))

    # 3. Problem Definition Agent 테스트
    if any([api_validation['openai'], api_validation['anthropic'], api_validation['google']]):
        result = await test_problem_definition_agent()
        results.append(("Problem Definition Agent", result))
    else:
        print("\n[SKIP] Problem Definition Agent 테스트 건너뜀 (API 키 없음)")
        results.append(("Problem Definition Agent", None))

    # 4. Orchestrator 워크플로우 테스트
    result = await test_orchestrator_workflow()
    results.append(("Orchestrator 워크플로우", result))

    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)

    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    for name, result in results:
        if result is True:
            print(f"[OK] {name}: 성공")
        elif result is False:
            print(f"[FAIL] {name}: 실패")
        else:
            print(f"[SKIP] {name}: 건너뜀")

    print(f"\n총 테스트: {len(results)}")
    print(f"성공: {passed}, 실패: {failed}, 건너뜀: {skipped}")

    if failed == 0 and passed > 0:
        print("\n[SUCCESS] Phase 3 기본 구현 성공!")
    elif failed > 0:
        print("\n[WARN] 일부 테스트 실패")
    else:
        print("\n[SKIP] 대부분의 테스트를 건너뛰었습니다 (API 키 설정 필요)")


if __name__ == "__main__":
    asyncio.run(main())
