"""
완전한 E2E 워크플로우 테스트
DA System의 전체 프로세스를 실제로 실행:
1. 데이터 업로드 및 세션 생성
2. Orchestrator Agent 실행
   - Problem Definition (문제 정의)
   - Research (선행 연구 조사)
   - Modeling (AutoML 학습)
   - Insight (SHAP 분석)
   - Reporting (리포트 생성)
3. 결과 검증
"""
import sys
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents import AgentContext, OrchestratorAgent
from app.services.llm import LLMRouter
from app.storage.file_manager import FileManager
from app.core.data_pipeline.loader import DataLoader


def print_section(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(step: str, status: str = ""):
    """단계 출력"""
    if status:
        print(f"[{status}] {step}")
    else:
        print(f"→ {step}")


async def main():
    print_section("DA SYSTEM - 완전한 E2E 워크플로우 테스트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ========================================================================
    # Step 1: 데이터 준비
    # ========================================================================
    print_section("Step 1: 데이터 업로드 및 준비")

    data_path = Path("data/titanic/train.csv")
    if not data_path.exists():
        print_step(f"❌ 데이터 파일을 찾을 수 없습니다: {data_path}", "ERROR")
        print_step("다운로드: https://www.kaggle.com/c/titanic/data", "INFO")
        return

    print_step(f"데이터 파일: {data_path}", "INFO")

    # 파일을 FileManager에 저장 (실제 API 호출처럼)
    with open(data_path, 'rb') as f:
        file_content = f.read()

    file_info = FileManager.save_upload(file_content, data_path.name)
    file_id = file_info["file_id"]
    saved_path = file_info["saved_path"]

    print_step(f"✅ 파일 업로드 완료", "SUCCESS")
    print(f"   - File ID: {file_id}")
    print(f"   - 저장 경로: {saved_path}")

    # 데이터 로드
    df, metadata = DataLoader.load_file(saved_path)

    # metadata 키 확인 (shape 또는 rows/columns)
    if 'shape' in metadata:
        rows, cols = metadata['shape']
    else:
        rows = metadata.get('rows', len(df))
        cols = metadata.get('columns', len(df.columns))

    print_step(f"✅ 데이터 로드 완료: {rows} rows × {cols} columns", "SUCCESS")

    # ========================================================================
    # Step 2: 세션 및 Context 생성
    # ========================================================================
    print_section("Step 2: 세션 생성 및 Context 초기화")

    session_id = str(uuid.uuid4())
    print_step(f"세션 ID: {session_id}", "INFO")

    # Redis 세션 생성 (Orchestrator가 상태를 저장하기 위해 필요)
    from app.storage.session_store import get_session_store

    session_store = get_session_store()
    session_data = {
        "file_id": file_id,
        "file_path": saved_path,
    }
    session_store.create_session(session_id, initial_data=session_data)
    print_step("✅ Redis 세션 생성 완료", "SUCCESS")

    # AgentContext 생성
    context = AgentContext(
        session_id=session_id,
        data={
            "file_id": file_id,
            "file_path": saved_path,
            # dataframe은 너무 크므로 제외 (ProblemDefinitionAgent가 file_path로 로드)
        },
        history=[]
    )

    print_step("✅ AgentContext 생성 완료", "SUCCESS")
    print(f"   - Session ID: {context.session_id}")
    print(f"   - Data keys: {list(context.data.keys())}")

    # ========================================================================
    # Step 3: LLM Provider 초기화
    # ========================================================================
    print_section("Step 3: LLM Provider 초기화")

    llm_router = LLMRouter()
    print_step("✅ LLM Router 초기화 완료", "SUCCESS")
    print(f"   - Default Provider: {llm_router.default_provider}")

    # ========================================================================
    # Step 4: Orchestrator Agent 실행
    # ========================================================================
    print_section("Step 4: Orchestrator Agent 실행 (전체 워크플로우)")

    orchestrator = OrchestratorAgent(context=context, llm_provider=llm_router)
    print_step("Orchestrator Agent 생성 완료", "INFO")

    print_step("⚙️  전체 워크플로우 시작...", "RUNNING")
    print("   예상 소요 시간: 15-30분 (Research 포함)")
    print("   단계: Problem Definition → Research → Modeling → Insight → Reporting")
    print()

    start_time = datetime.now()

    try:
        result = await orchestrator.execute()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if result.success:
            print_step(f"✅ 워크플로우 완료! (소요 시간: {duration:.1f}초 = {duration/60:.1f}분)", "SUCCESS")
        else:
            print_step(f"❌ 워크플로우 실패: {result.error}", "FAILED")
            return

    except Exception as e:
        print_step(f"❌ 예외 발생: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # Step 5: 결과 검증
    # ========================================================================
    print_section("Step 5: 결과 검증")

    workflow_data = result.data

    # 5.1 Problem Definition 검증
    print_step("Problem Definition 결과", "CHECK")
    problem_def = workflow_data.get("problem_definition", {})
    if problem_def:
        print(f"   - 문제 유형: {problem_def.get('problem_type', 'N/A')}")
        print(f"   - 타겟 변수: {problem_def.get('target_column', 'N/A')}")
        print(f"   - 평가 지표: {problem_def.get('evaluation_metric', 'N/A')}")
        print(f"   - 분석 목표: {problem_def.get('analysis_goal', 'N/A')[:80]}...")
    else:
        print("   ❌ Problem Definition 데이터 없음")

    # 5.2 Research 검증
    print_step("Research 결과", "CHECK")
    research = workflow_data.get("research", {})
    if research:
        papers = research.get("papers", [])
        kaggle = research.get("kaggle_solutions", [])
        deep_research = research.get("deep_research", {})

        print(f"   - 논문: {len(papers)}개 발견")
        print(f"   - Kaggle 솔루션: {len(kaggle)}개 발견")
        print(f"   - DeepResearch: {'있음' if deep_research else '없음'}")
    else:
        print("   ⚠️  Research 데이터 없음 (에러 허용)")

    # 5.3 Modeling 검증
    print_step("Modeling 결과", "CHECK")
    modeling = workflow_data.get("modeling", {})
    if modeling:
        model_data = modeling.get("model_data", {})
        metrics = model_data.get("metrics", {})

        print(f"   - Best Estimator: {model_data.get('best_estimator', 'N/A')}")
        print(f"   - MLflow Run ID: {model_data.get('run_id', 'N/A')}")
        print(f"   - Metrics:")
        for metric_name, metric_value in list(metrics.items())[:5]:
            if isinstance(metric_value, float):
                print(f"     * {metric_name}: {metric_value:.4f}")
            else:
                print(f"     * {metric_name}: {metric_value}")
    else:
        print("   ❌ Modeling 데이터 없음")

    # 5.4 Insight 검증
    print_step("Insight 결과", "CHECK")
    insights = workflow_data.get("insight", {})
    if insights:
        key_findings = insights.get("key_findings", [])
        business_insights = insights.get("business_insights", [])
        recommendations = insights.get("recommendations", [])

        print(f"   - 주요 발견: {len(key_findings)}개")
        if key_findings:
            print(f"     예: {key_findings[0][:80]}...")

        print(f"   - 비즈니스 인사이트: {len(business_insights)}개")
        print(f"   - 권장사항: {len(recommendations)}개")
    else:
        print("   ❌ Insight 데이터 없음")

    # 5.5 Report 검증
    print_step("Report 결과", "CHECK")
    report = workflow_data.get("report", {})
    if report:
        markdown_report = report.get("markdown_report")
        html_report = report.get("html_report")
        artifacts_zip = report.get("artifacts_zip")

        print(f"   - Markdown 리포트: {markdown_report if markdown_report else 'N/A'}")
        print(f"   - HTML 리포트: {html_report if html_report else 'N/A'}")
        print(f"   - Artifacts ZIP: {artifacts_zip if artifacts_zip else 'N/A'}")

        # 파일 존재 확인
        if markdown_report and Path(markdown_report).exists():
            print(f"   ✅ Markdown 리포트 생성됨 ({Path(markdown_report).stat().st_size} bytes)")
        if html_report and Path(html_report).exists():
            print(f"   ✅ HTML 리포트 생성됨 ({Path(html_report).stat().st_size} bytes)")
    else:
        print("   ❌ Report 데이터 없음")

    # ========================================================================
    # Summary
    # ========================================================================
    print_section("테스트 완료 요약")

    phases_completed = []
    phases_failed = []

    if problem_def:
        phases_completed.append("Problem Definition")
    else:
        phases_failed.append("Problem Definition")

    if research:
        phases_completed.append("Research")
    else:
        phases_failed.append("Research")

    if modeling:
        phases_completed.append("Modeling")
    else:
        phases_failed.append("Modeling")

    if insights:
        phases_completed.append("Insight")
    else:
        phases_failed.append("Insight")

    if report:
        phases_completed.append("Reporting")
    else:
        phases_failed.append("Reporting")

    print(f"✅ 완료된 단계 ({len(phases_completed)}/5): {', '.join(phases_completed)}")
    if phases_failed:
        print(f"❌ 실패한 단계 ({len(phases_failed)}/5): {', '.join(phases_failed)}")

    print(f"\n총 소요 시간: {duration:.1f}초 ({duration/60:.1f}분)")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 최종 판정
    if len(phases_completed) == 5:
        print("\n" + "🎉 " * 20)
        print("   전체 E2E 테스트 성공! DA System이 정상 작동합니다!")
        print("🎉 " * 20)
    elif len(phases_completed) >= 3:
        print("\n⚠️  부분 성공: 핵심 기능은 작동하지만 일부 단계가 누락되었습니다.")
    else:
        print("\n❌ 테스트 실패: 주요 단계들이 작동하지 않습니다.")

    # 리포트 경로 안내
    if markdown_report:
        print(f"\n📄 생성된 리포트를 확인하세요:")
        print(f"   Markdown: {markdown_report}")
        if html_report:
            print(f"   HTML: {html_report}")


if __name__ == "__main__":
    asyncio.run(main())
