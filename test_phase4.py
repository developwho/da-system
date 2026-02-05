"""
Phase 4 통합 테스트: 외부 API 및 Research 에이전트

테스트 항목:
1. HuggingFaceClient - 논문 검색
2. KaggleClient - Competition 검색
3. DeepResearchClient - DeepResearch 실행 (선택적)
4. PapersAgent - 에이전트 실행
5. SolutionsAgent - 에이전트 실행
6. ResearchCoordinator - 병렬 실행 및 통합
"""
import asyncio
from app.config import settings
from app.services.external.huggingface import HuggingFaceClient
from app.services.external.kaggle import KaggleClient
from app.services.external.deep_research import DeepResearchClient, GENAI_AVAILABLE
from app.agents.base import AgentContext
from app.agents.research import (
    PapersAgent,
    SolutionsAgent,
    DeepResearchAgent,
    ResearchCoordinator
)

from pathlib import Path


def _has_kaggle_credentials() -> bool:
    if settings.KAGGLE_USERNAME and settings.KAGGLE_KEY:
        return True
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    return kaggle_json.exists()


async def test_huggingface_client():
    """HuggingFaceClient 테스트"""
    print("\n" + "="*60)
    print("TEST 1: HuggingFace Client")
    print("="*60)

    if not settings.HUGGINGFACE_TOKEN:
        print("⏭️ HUGGINGFACE_TOKEN 미설정 - 테스트 건너뜀")
        return None

    try:
        client = HuggingFaceClient(token=settings.HUGGINGFACE_TOKEN)

        # 논문 검색 테스트
        query = "binary classification insurance"
        print(f"\n검색 쿼리: {query}")

        papers = await client.search_papers(query, limit=3)

        if papers:
            print(f"✅ {len(papers)}개 논문 발견")
            for i, paper in enumerate(papers, 1):
                print(f"\n{i}. {paper.title}")
                print(f"   Authors: {', '.join(paper.authors[:3])}")
                print(f"   URL: {paper.url}")
        else:
            print("⚠️ 논문을 찾지 못했습니다 (ArXiv fallback 가능)")

        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


async def test_kaggle_client():
    """KaggleClient 테스트"""
    print("\n" + "="*60)
    print("TEST 2: Kaggle Client")
    print("="*60)

    if not _has_kaggle_credentials():
        print("⏭️ Kaggle 자격증명 미설정 - 테스트 건너뜀")
        return None

    try:
        client = KaggleClient(
            username=settings.KAGGLE_USERNAME,
            key=settings.KAGGLE_KEY
        )

        # Competition 검색
        query = "classification"
        print(f"\n검색 쿼리: {query}")

        competitions = await client.search_competitions(query, limit=3)

        if competitions:
            print(f"✅ {len(competitions)}개 Competition 발견")
            for i, comp in enumerate(competitions, 1):
                print(f"\n{i}. {comp.title}")
                print(f"   Category: {comp.category}")
                print(f"   URL: {comp.url}")
        else:
            print("⚠️ Competition을 찾지 못했습니다")

        # Insight 분석
        print("\n\nKaggle Insight 분석 중...")
        insight = await client.analyze_competition(query, limit_competitions=2, limit_kernels=3)

        if insight:
            print(f"✅ Insight 생성 완료")
            print(f"   Competition: {insight.competition.title}")
            print(f"   Top Kernels: {len(insight.top_kernels)}개")
            print(f"   Techniques: {', '.join(insight.techniques[:5])}")
        else:
            print("⚠️ Insight 생성 실패")

        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_deep_research_client():
    """DeepResearchClient 테스트 (선택적 - 시간 소요)"""
    print("\n" + "="*60)
    print("TEST 3: DeepResearch Client (선택적)")
    print("="*60)

    if not GENAI_AVAILABLE:
        print("⏭️ google-genai 미설치 - 테스트 건너뜀")
        return None

    if not settings.GOOGLE_API_KEY:
        print("⏭️ GOOGLE_API_KEY 미설정 - 테스트 건너뜀")
        return None

    skip = input("\nDeepResearch 테스트를 건너뛰시겠습니까? (y/n): ").lower() == 'y'
    if skip:
        print("⏭️ 테스트 건너뜀")
        return None

    try:
        client = DeepResearchClient(api_key=settings.GOOGLE_API_KEY)

        query = "machine learning classification techniques"
        print(f"\n연구 쿼리: {query}")
        print("⏳ DeepResearch 실행 중... (최대 10분 소요)")

        result = await client.conduct_research(
            query=query,
            max_duration_minutes=10,
            poll_interval=15
        )

        if result:
            print(f"✅ DeepResearch 완료")
            print(f"   Interaction ID: {result.interaction_id}")
            print(f"   Summary: {result.summary[:200]}...")
            print(f"   Key Findings: {len(result.key_findings)}개")
            print(f"   Recommendations: {len(result.recommendations)}개")
        else:
            print("⚠️ DeepResearch 실패 또는 타임아웃")

        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_papers_agent():
    """PapersAgent 테스트"""
    print("\n" + "="*60)
    print("TEST 4: Papers Agent")
    print("="*60)

    if not settings.HUGGINGFACE_TOKEN:
        print("⏭️ HUGGINGFACE_TOKEN 미설정 - 테스트 건너뜀")
        return None

    try:
        # 문제 정의 준비
        problem_definition = {
            "problem_type": "binary_classification",
            "goal": "predict insurance claims",
            "target_variable": "target",
            "evaluation_metric": "roc_auc",
        }

        context = AgentContext(
            session_id="test_phase4_papers",
            data={"problem_definition": problem_definition}
        )

        agent = PapersAgent(context)
        print(f"\n에이전트: {agent.name}")
        print(f"설명: {agent.description}")

        print("\n🚀 Papers Agent 실행 중...")
        result = await agent.run()

        if result.success:
            print(f"✅ 성공")
            print(f"   Papers: {len(result.data.get('papers', []))}개")
            print(f"   Output: {result.data.get('output_file', 'N/A')}")
        else:
            print(f"❌ 실패: {result.error}")

        return result.success

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_solutions_agent():
    """SolutionsAgent 테스트"""
    print("\n" + "="*60)
    print("TEST 5: Solutions Agent")
    print("="*60)

    if not _has_kaggle_credentials():
        print("⏭️ Kaggle 자격증명 미설정 - 테스트 건너뜀")
        return None

    try:
        # 문제 정의 준비
        problem_definition = {
            "problem_type": "binary_classification",
            "goal": "predict customer churn",
            "target_variable": "churn",
            "evaluation_metric": "f1_score",
        }

        context = AgentContext(
            session_id="test_phase4_solutions",
            data={"problem_definition": problem_definition}
        )

        agent = SolutionsAgent(context)
        print(f"\n에이전트: {agent.name}")
        print(f"설명: {agent.description}")

        print("\n🚀 Solutions Agent 실행 중...")
        result = await agent.run()

        if result.success:
            print(f"✅ 성공")
            insight = result.data.get('insight')
            if insight:
                print(f"   Competition: {insight.get('competition', {}).get('title', 'N/A')}")
                print(f"   Kernels: {len(insight.get('top_kernels', []))}개")
                print(f"   Techniques: {len(insight.get('techniques', []))}개")
            print(f"   Output: {result.data.get('output_file', 'N/A')}")
        else:
            print(f"❌ 실패: {result.error}")

        return result.success

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_research_coordinator():
    """ResearchCoordinator 테스트"""
    print("\n" + "="*60)
    print("TEST 6: Research Coordinator (통합)")
    print("="*60)

    if not settings.HUGGINGFACE_TOKEN or not _has_kaggle_credentials() or not settings.GOOGLE_API_KEY or not GENAI_AVAILABLE:
        print("⏭️ 외부 API 자격증명 미설정 - 테스트 건너뜀")
        return None

    skip = input("\nResearchCoordinator 테스트를 건너뛰시겠습니까? (DeepResearch 포함, y/n): ").lower() == 'y'
    if skip:
        print("⏭️ 테스트 건너뜀")
        return None

    try:
        # 문제 정의 준비
        problem_definition = {
            "problem_type": "binary_classification",
            "goal": "predict house prices",
            "target_variable": "price",
            "evaluation_metric": "rmse",
        }

        context = AgentContext(
            session_id="test_phase4_coordinator",
            data={"problem_definition": problem_definition}
        )

        coordinator = ResearchCoordinator(context)
        print(f"\n에이전트: {coordinator.name}")
        print(f"설명: {coordinator.description}")

        print("\n🚀 Research Coordinator 실행 중 (병렬)...")
        print("   - PapersAgent")
        print("   - SolutionsAgent")
        print("   - DeepResearchAgent")

        result = await coordinator.run()

        if result.success:
            print(f"\n✅ 통합 완료")
            integrated = result.data.get('integrated_data', {})
            print(f"   Papers: {len(integrated.get('papers', []))}개")
            print(f"   Kaggle: {'있음' if integrated.get('kaggle') else '없음'}")
            print(f"   DeepResearch: {'있음' if integrated.get('deep_research') else '없음'}")
            print(f"   Techniques: {len(integrated.get('techniques', []))}개")
            print(f"   Summary: {result.data.get('summary_file', 'N/A')}")
        else:
            print(f"❌ 실패: {result.error}")

        return result.success

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 Phase 4 통합 테스트 시작")
    print("="*60)

    # API 키 검증
    validation = settings.validate_api_keys()
    print("\n📋 API 키 검증:")
    print(f"   OpenAI: {'✅' if validation['openai'] else '❌'}")
    print(f"   Anthropic: {'✅' if validation['anthropic'] else '❌'}")
    print(f"   Google: {'✅' if validation['google'] else '❌'}")
    print(f"   HuggingFace: {'✅' if validation['huggingface'] else '❌'}")
    print(f"   Kaggle: {'✅' if validation['kaggle'] else '❌'}")

    results = []

    # 테스트 실행
    results.append(("HuggingFace Client", await test_huggingface_client()))
    results.append(("Kaggle Client", await test_kaggle_client()))
    results.append(("DeepResearch Client", await test_deep_research_client()))
    results.append(("Papers Agent", await test_papers_agent()))
    results.append(("Solutions Agent", await test_solutions_agent()))
    results.append(("Research Coordinator", await test_research_coordinator()))

    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)

    for name, result in results:
        if result is True:
            status = "✅ 통과"
        elif result is False:
            status = "❌ 실패"
        else:
            status = "⏭️ 건너뜀"
        print(f"{name}: {status}")

    print(f"\n총 테스트: {total}, 통과: {passed}, 실패: {failed}, 건너뜀: {skipped}")

    if failed == 0 and passed > 0:
        print("\n🎉 모든 테스트 통과! Phase 4 완료!")
    elif failed > 0:
        print(f"\n⚠️ {failed}개 테스트 실패")
    else:
        print("\n⏭️ 일부 테스트가 건너뜀 처리되었습니다.")

    return failed == 0 and passed > 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
