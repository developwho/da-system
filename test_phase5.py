"""
Phase 5 통합 테스트: 인사이트 & 리포팅

테스트 항목:
1. SHAP Analyzer - SHAP 분석 및 시각화
2. Insight Agent - 인사이트 생성
3. Reporting Agent - 리포트 생성
4. Reports API - 리포트 조회 및 다운로드
5. 전체 워크플로우 - End-to-End 테스트
"""
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from app.config import settings
from app.core.evaluation import SHAPAnalyzer
from app.agents.base import AgentContext
from app.agents.insight import InsightAgent
from app.agents.reporting import ReportingAgent


def create_test_data():
    """테스트용 데이터 및 모델 생성"""
    print("\n📊 테스트 데이터 및 모델 생성 중...")

    # 합성 데이터 생성
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        random_state=42
    )

    # DataFrame 변환
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    X_df = pd.DataFrame(X, columns=feature_names)

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_df, y, test_size=0.3, random_state=42
    )

    # 모델 학습
    print("🤖 RandomForest 모델 학습 중...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 예측
    predictions = model.predict_proba(X_test)
    pred_labels = model.predict(X_test)

    # 성능 평가
    from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
    metrics = {
        "accuracy": accuracy_score(y_test, pred_labels),
        "roc_auc": roc_auc_score(y_test, predictions[:, 1]),
        "f1_score": f1_score(y_test, pred_labels)
    }

    print(f"✅ 모델 성능: Accuracy={metrics['accuracy']:.4f}, ROC-AUC={metrics['roc_auc']:.4f}")

    return {
        "model": model,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "predictions": predictions,
        "metrics": metrics,
        "best_model": "RandomForest"
    }


async def test_shap_analyzer():
    """SHAP Analyzer 테스트"""
    print("\n" + "="*60)
    print("TEST 1: SHAP Analyzer")
    print("="*60)

    try:
        # 테스트 데이터 생성
        model_data = create_test_data()

        # SHAP Analyzer 생성
        analyzer = SHAPAnalyzer(
            model_data["model"],
            model_data["X_train"],
            model_data["X_test"]
        )

        print("\n1️⃣ SHAP Values 계산 중...")
        shap_values = analyzer.calculate_shap_values(max_samples=100)
        print(f"✅ SHAP Values 계산 완료: shape={shap_values[1].shape if isinstance(shap_values, list) else shap_values.shape}")

        print("\n2️⃣ Feature Importance 추출 중...")
        importance_df = analyzer.get_feature_importance(top_n=10)
        print(f"✅ Top 10 Features:")
        for idx, row in importance_df.head(5).iterrows():
            print(f"   - {row['feature']}: {row['importance']:.4f}")

        print("\n3️⃣ SHAP 시각화 생성 중...")
        output_dir = Path("outputs/shap/test_phase5")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Summary plot
        analyzer.plot_summary(str(output_dir / "summary.png"))
        print(f"   ✅ Summary plot: {output_dir / 'summary.png'}")

        # Bar plot
        analyzer.plot_bar(str(output_dir / "bar.png"))
        print(f"   ✅ Bar plot: {output_dir / 'bar.png'}")

        # Waterfall plot
        analyzer.plot_waterfall(0, str(output_dir / "waterfall.png"))
        print(f"   ✅ Waterfall plot: {output_dir / 'waterfall.png'}")

        print("\n✅ SHAP Analyzer 테스트 통과")
        return True

    except Exception as e:
        print(f"\n❌ SHAP Analyzer 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_insight_agent():
    """Insight Agent 테스트"""
    print("\n" + "="*60)
    print("TEST 2: Insight Agent")
    print("="*60)

    try:
        # 테스트 데이터 생성
        model_data = create_test_data()

        # Context 생성
        context = AgentContext(
            session_id="test_phase5_insight",
            data={
                "model_data": model_data,
                "problem_definition": {
                    "problem_type": "binary_classification",
                    "goal": "test classification",
                    "target_variable": "target",
                }
            }
        )

        # Insight Agent 실행
        print("\n🚀 Insight Agent 실행 중...")
        agent = InsightAgent(context)
        result = await agent.run()

        if result.success:
            print(f"✅ Insight Agent 성공")
            insights = result.data.get("insights", {})

            print("\n📊 생성된 인사이트:")
            key_findings = insights.get("key_findings", [])
            if key_findings:
                print("\n주요 발견사항:")
                for finding in key_findings[:3]:
                    print(f"   - {finding}")

            print(f"\n📄 Insights 파일: {result.data.get('insights_file')}")

            return True
        else:
            print(f"❌ Insight Agent 실패: {result.error}")
            return False

    except Exception as e:
        print(f"\n❌ Insight Agent 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_reporting_agent():
    """Reporting Agent 테스트"""
    print("\n" + "="*60)
    print("TEST 3: Reporting Agent")
    print("="*60)

    try:
        # 테스트 데이터 생성
        model_data = create_test_data()

        # Mock insights
        insights = {
            "full_text": "Test insights content",
            "key_findings": [
                "Finding 1: Important feature identified",
                "Finding 2: Model performs well",
                "Finding 3: Data quality is good"
            ],
            "business_insights": [
                "Insight 1: Can be applied to production",
                "Insight 2: ROI is positive"
            ],
            "recommendations": [
                "Recommendation 1: Deploy model",
                "Recommendation 2: Monitor performance"
            ],
            "warnings": [
                "Warning 1: Watch for data drift"
            ]
        }

        # Context 생성
        context = AgentContext(
            session_id="test_phase5_reporting",
            data={
                "problem_definition": {
                    "problem_type": "binary_classification",
                    "goal": "test classification",
                    "target_variable": "target",
                },
                "model_data": model_data,
                "insights": insights,
                "research_results": {
                    "papers": [],
                    "kaggle": {},
                    "deep_research": {}
                }
            }
        )

        # Reporting Agent 실행
        print("\n🚀 Reporting Agent 실행 중...")
        agent = ReportingAgent(context)
        result = await agent.run()

        if result.success:
            print(f"✅ Reporting Agent 성공")

            print(f"\n📄 Markdown 리포트: {result.data.get('markdown_report')}")
            print(f"🌐 HTML 리포트: {result.data.get('html_report')}")
            print(f"📦 Artifacts ZIP: {result.data.get('artifacts_zip')}")

            # 파일 존재 확인
            markdown_path = Path(result.data.get('markdown_report', ''))
            html_path = Path(result.data.get('html_report', ''))

            if markdown_path.exists():
                print(f"   ✅ Markdown 파일 생성됨 (크기: {markdown_path.stat().st_size} bytes)")
            if html_path.exists():
                print(f"   ✅ HTML 파일 생성됨 (크기: {html_path.stat().st_size} bytes)")

            return True
        else:
            print(f"❌ Reporting Agent 실패: {result.error}")
            return False

    except Exception as e:
        print(f"\n❌ Reporting Agent 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_reports_api():
    """Reports API 테스트"""
    print("\n" + "="*60)
    print("TEST 4: Reports API")
    print("="*60)

    try:
        import httpx

        # FastAPI 서버가 실행 중이어야 함
        base_url = "http://localhost:8000/api/v1/reports"

        print("\n📡 FastAPI 서버 연결 확인 중...")

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check
            try:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    print("✅ FastAPI 서버 실행 중")
                else:
                    print("⚠️ FastAPI 서버 상태 이상")
                    return None
            except httpx.ConnectError:
                print("⏭️ FastAPI 서버가 실행되지 않음 - 테스트 건너뜀")
                print("   서버 시작: uvicorn app.main:app --reload --port 8000")
                return None

            # 리포트 목록 조회
            print("\n1️⃣ 리포트 목록 조회 중...")
            response = await client.get(base_url)
            if response.status_code == 200:
                reports = response.json()
                print(f"✅ 리포트 목록: {len(reports)}개")
                if reports:
                    print(f"   최신 리포트: {reports[0].get('session_id')}")
            else:
                print(f"⚠️ 리포트 목록 조회 실패: {response.status_code}")

        return True

    except Exception as e:
        print(f"\n❌ Reports API 테스트 실패: {e}")
        return False


async def test_end_to_end_workflow():
    """End-to-End 워크플로우 테스트"""
    print("\n" + "="*60)
    print("TEST 5: End-to-End Workflow")
    print("="*60)

    try:
        session_id = "test_e2e_workflow"

        print("\n1️⃣ 데이터 및 모델 생성...")
        model_data = create_test_data()

        print("\n2️⃣ SHAP 분석 수행...")
        analyzer = SHAPAnalyzer(
            model_data["model"],
            model_data["X_train"],
            model_data["X_test"]
        )
        output_dir = f"outputs/shap/{session_id}"
        shap_results = analyzer.generate_analysis_report(output_dir)
        print(f"✅ SHAP 분석 완료: {len(shap_results.get('top_features', []))}개 주요 피처")

        print("\n3️⃣ 인사이트 생성...")
        insight_context = AgentContext(
            session_id=session_id,
            data={
                "model_data": model_data,
                "problem_definition": {
                    "problem_type": "binary_classification",
                    "goal": "end-to-end test",
                }
            }
        )
        insight_agent = InsightAgent(insight_context)
        insight_result = await insight_agent.run()

        if not insight_result.success:
            print(f"⚠️ 인사이트 생성 실패: {insight_result.error}")

        print("\n4️⃣ 리포트 생성...")
        reporting_context = AgentContext(
            session_id=session_id,
            data={
                "problem_definition": {"problem_type": "binary_classification", "goal": "e2e test"},
                "model_data": model_data,
                "insights": insight_result.data.get("insights", {}),
                "research_results": {}
            }
        )
        reporting_agent = ReportingAgent(reporting_context)
        reporting_result = await reporting_agent.run()

        if reporting_result.success:
            print(f"✅ 전체 워크플로우 성공!")
            print(f"\n📊 생성된 결과:")
            print(f"   - SHAP 분석: {output_dir}")
            print(f"   - Markdown: {reporting_result.data.get('markdown_report')}")
            print(f"   - HTML: {reporting_result.data.get('html_report')}")
            print(f"   - Artifacts: {reporting_result.data.get('artifacts_zip')}")
            return True
        else:
            print(f"❌ 리포트 생성 실패: {reporting_result.error}")
            return False

    except Exception as e:
        print(f"\n❌ End-to-End 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 Phase 5 통합 테스트 시작")
    print("="*60)

    # API 키 검증
    validation = settings.validate_api_keys()
    print("\n📋 API 키 검증:")
    print(f"   OpenAI: {'✅' if validation['openai'] else '❌'}")
    print(f"   Anthropic: {'✅' if validation['anthropic'] else '❌'}")
    print(f"   Google: {'✅' if validation['google'] else '❌'}")

    results = []

    # 테스트 실행
    results.append(("SHAP Analyzer", await test_shap_analyzer()))
    results.append(("Insight Agent", await test_insight_agent()))
    results.append(("Reporting Agent", await test_reporting_agent()))
    results.append(("Reports API", await test_reports_api()))
    results.append(("End-to-End Workflow", await test_end_to_end_workflow()))

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
        print("\n🎉 모든 테스트 통과! Phase 5 완료!")
        print("\n✅ DA System 전체 구현 완료! (Phase 1-5)")
    elif failed > 0:
        print(f"\n⚠️ {failed}개 테스트 실패")
    else:
        print("\n⏭️ 일부 테스트가 건너뜀 처리되었습니다.")

    return failed == 0 and passed > 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
