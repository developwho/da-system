"""
Orchestrator 통합 테스트
"""
import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

from app.agents.base import AgentContext
from app.agents.orchestrator import OrchestratorAgent
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_orchestrator_integration():
    """
    Orchestrator 통합 테스트

    이 테스트는 실제 데이터 파일이 필요합니다:
    - Porto Seguro 데이터: data/porto_seguro_safe_driver_train.csv
    """
    print("\n" + "="*80)
    print("Orchestrator Integration Test")
    print("="*80 + "\n")

    # 테스트 데이터 확인
    test_data_path = Path("data/porto_seguro_safe_driver_train.csv")
    if not test_data_path.exists():
        print(f"⚠️  Test data not found: {test_data_path}")
        print("   Skipping test...")
        return False

    try:
        # 1. 파일 업로드 시뮬레이션
        print("1. Uploading test data...")
        from app.storage.file_manager import FileManager

        file_id = FileManager.save_uploaded_file(
            str(test_data_path),
            "porto_seguro_safe_driver_train.csv"
        )
        print(f"   ✓ File uploaded: {file_id}")

        # 2. Context 생성
        print("\n2. Creating agent context...")
        context = AgentContext(
            session_id="test_orchestrator_001",
            data={
                "file_id": file_id,
                "target_column": "target",
                "problem_type": "binary_classification"
            }
        )
        print(f"   ✓ Context created: session_id={context.session_id}")

        # 3. Orchestrator 실행
        print("\n3. Running Orchestrator...")
        print("-" * 80)

        orchestrator = OrchestratorAgent(context)
        result = await orchestrator.run()

        print("-" * 80)

        # 4. 결과 확인
        print("\n4. Checking results...")
        if result.success:
            print(f"   ✓ Orchestrator completed successfully!")
            print(f"   - Workflow state: {result.data.get('workflow_state')}")

            # 각 단계 결과 확인
            if result.data.get('problem_definition'):
                pd = result.data['problem_definition']
                print(f"\n   Problem Definition:")
                print(f"     - Problem type: {pd.get('problem_type')}")
                print(f"     - Target column: {pd.get('target_column')}")
                print(f"     - Evaluation metric: {pd.get('evaluation_metric')}")

            if result.data.get('research'):
                research = result.data['research']
                print(f"\n   Research:")
                papers = research.get('papers', [])
                print(f"     - Papers found: {len(papers)}")

            if result.data.get('modeling'):
                modeling = result.data['modeling']
                print(f"\n   Modeling:")
                print(f"     - Best estimator: {modeling.get('best_estimator')}")
                print(f"     - Metrics: {modeling.get('metrics')}")

            if result.data.get('insight'):
                insight = result.data['insight']
                print(f"\n   Insights:")
                insights_list = insight.get('insights', [])
                print(f"     - Insights generated: {len(insights_list)}")

            if result.data.get('report'):
                report = result.data['report']
                print(f"\n   Reports:")
                print(f"     - Markdown: {report.get('markdown_report')}")
                print(f"     - HTML: {report.get('html_report')}")

            print(f"\n   ✓ All phases completed!")
            return True
        else:
            print(f"   ✗ Orchestrator failed: {result.error}")
            return False

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestrator_error_handling():
    """Orchestrator 에러 핸들링 테스트"""
    print("\n" + "="*80)
    print("Orchestrator Error Handling Test")
    print("="*80 + "\n")

    try:
        # 잘못된 데이터로 테스트
        print("1. Testing with invalid file_id...")
        context = AgentContext(
            session_id="test_orchestrator_error_001",
            data={
                "file_id": "invalid_file_id",
                "target_column": "target"
            }
        )

        orchestrator = OrchestratorAgent(context)
        result = await orchestrator.run()

        if not result.success:
            print(f"   ✓ Orchestrator correctly failed: {result.error}")
            return True
        else:
            print(f"   ✗ Orchestrator should have failed but didn't")
            return False

    except Exception as e:
        print(f"   ✗ Unexpected exception: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("ORCHESTRATOR INTEGRATION TEST SUITE")
    print("="*80)

    results = {
        "integration": False,
        "error_handling": False
    }

    # 비동기 테스트 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Integration Test
        results["integration"] = loop.run_until_complete(test_orchestrator_integration())

        # Error Handling Test
        results["error_handling"] = loop.run_until_complete(test_orchestrator_error_handling())

    finally:
        loop.close()

    # 결과 요약
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Integration Test:     {'PASS ✓' if results['integration'] else 'FAIL ✗'}")
    print(f"Error Handling Test:  {'PASS ✓' if results['error_handling'] else 'FAIL ✗'}")
    print("="*80 + "\n")

    all_passed = all(results.values())
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
