"""
전체 워크플로우 E2E 테스트
Orchestrator Agent를 통한 전체 파이프라인 검증:
문제 정의 → 선행연구 → 모델링 → 인사이트 → 리포팅
"""
import sys
import asyncio
from pathlib import Path
import pandas as pd

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.orchestrator import OrchestratorAgent
from app.agents.base import AgentContext
from app.storage.session_store import SessionStore
from app.core.data_pipeline.loader import DataLoader

print("=" * 80)
print("FULL WORKFLOW E2E TEST - DA System")
print("=" * 80)

# ============================================================================
# Phase 0: 초기화
# ============================================================================
print("\n[Phase 0] Initialization")
print("-" * 80)

# Session Store 초기화
session_store = SessionStore()
session_id = session_store.create_session({
    "user_id": "test_user",
    "created_at": session_store._get_current_time()
})
print(f"Session created: {session_id}")

# 데이터 로드
data_path = Path("data/titanic/train.csv")
print(f"Loading data from: {data_path}")

loader = DataLoader()
df, metadata = loader.load_file(data_path)
print(f"OK Loaded {len(df)} rows, {len(df.columns)} columns")

# AgentContext 생성
context = AgentContext(
    session_id=session_id,
    data={
        "data_file_path": str(data_path),
        "dataframe": df,
        "file_metadata": metadata,
        "user_input": "Titanic 데이터셋에서 생존자를 예측하고 싶습니다. 어떤 요인이 생존에 영향을 미쳤는지도 알고 싶어요."
    }
)

# ============================================================================
# Orchestrator 실행
# ============================================================================
print("\n[Orchestrator] Starting Full Workflow")
print("=" * 80)

orchestrator = OrchestratorAgent(
    llm_provider="openai",
    model_name="gpt-4",
    session_store=session_store
)

print(f"Orchestrator initialized: {orchestrator.agent_id}")
print(f"LLM Provider: {orchestrator.llm_provider}")
print(f"Model: {orchestrator.model_name}")

# 비동기 실행
async def run_workflow():
    try:
        print("\n[*] Running workflow...")
        result = await orchestrator.run(context)

        print("\n" + "=" * 80)
        print("WORKFLOW RESULT")
        print("=" * 80)

        # 결과 출력
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Current State: {result.get('current_state', 'N/A')}")

        # 각 단계 결과
        if 'results' in result:
            results = result['results']

            # Problem Definition
            if 'problem_definition' in results:
                print("\n[1] Problem Definition:")
                pd_result = results['problem_definition']
                print(f"    Status: {pd_result.get('status', 'N/A')}")
                if 'problem_statement' in pd_result:
                    print(f"    Problem: {pd_result['problem_statement'][:100]}...")

            # Research
            if 'research' in results:
                print("\n[2] Research:")
                research_result = results['research']
                print(f"    Status: {research_result.get('status', 'N/A')}")
                if 'summary' in research_result:
                    print(f"    Summary available: {len(research_result['summary'])} chars")

            # Modeling
            if 'modeling' in results:
                print("\n[3] Modeling:")
                modeling_result = results['modeling']
                print(f"    Status: {modeling_result.get('status', 'N/A')}")
                if 'best_model' in modeling_result:
                    print(f"    Best Model: {modeling_result['best_model']}")
                if 'metrics' in modeling_result:
                    metrics = modeling_result['metrics']
                    print(f"    Metrics: {metrics}")

            # Insight
            if 'insight' in results:
                print("\n[4] Insight:")
                insight_result = results['insight']
                print(f"    Status: {insight_result.get('status', 'N/A')}")
                if 'insights' in insight_result:
                    insights = insight_result['insights']
                    print(f"    Insights: {len(insights)} findings")

            # Reporting
            if 'reporting' in results:
                print("\n[5] Reporting:")
                report_result = results['reporting']
                print(f"    Status: {report_result.get('status', 'N/A')}")
                if 'report_path' in report_result:
                    print(f"    Report: {report_result['report_path']}")

        # 오류 출력
        if 'errors' in result:
            print("\n[!] Errors:")
            for error in result['errors']:
                print(f"    - {error}")

        return result

    except Exception as e:
        print(f"\n[X] Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# 실행
print("\n" + "=" * 80)
print("Starting async workflow execution...")
print("=" * 80)

result = asyncio.run(run_workflow())

# ============================================================================
# 결과 검증
# ============================================================================
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

if result:
    # 세션 상태 확인
    session_data = session_store.get_session(session_id)
    if session_data:
        print(f"\nSession Status:")
        print(f"  Session ID: {session_id}")
        print(f"  Workflow State: {session_data.get('workflow_state', 'N/A')}")
        print(f"  Message Count: {len(session_data.get('messages', []))}")

    # 출력 파일 확인
    outputs_dir = Path("outputs")

    # Research 출력
    research_dir = outputs_dir / "research" / session_id
    if research_dir.exists():
        research_files = list(research_dir.glob("*.md"))
        print(f"\nResearch Outputs: {len(research_files)} files")
        for f in research_files:
            print(f"  - {f.name}")

    # Model 출력
    models_dir = outputs_dir / "models" / session_id
    if models_dir.exists():
        model_files = list(models_dir.glob("**/*"))
        print(f"\nModel Outputs: {len(model_files)} files")
        for f in model_files[:5]:  # First 5
            print(f"  - {f.name}")

    # Report 출력
    reports_dir = outputs_dir / "reports" / session_id
    if reports_dir.exists():
        report_files = list(reports_dir.glob("*"))
        print(f"\nReport Outputs: {len(report_files)} files")
        for f in report_files:
            print(f"  - {f.name}")

    print("\n" + "=" * 80)
    if result.get('status') == 'completed':
        print("*** FULL WORKFLOW TEST PASSED! ***")
    else:
        print("*** WORKFLOW INCOMPLETE ***")
    print("=" * 80)
else:
    print("\n*** WORKFLOW TEST FAILED ***")
    print("=" * 80)
