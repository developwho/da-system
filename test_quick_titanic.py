"""
빠른 Titanic 테스트 - 타겟 컬럼 직접 지정
Survived (생존 여부)를 타겟으로 binary classification 테스트
"""
import sys
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.agents import AgentContext, OrchestratorAgent
from app.services.llm import LLMRouter
from app.storage.file_manager import FileManager
from app.storage.session_store import get_session_store
from app.core.data_pipeline.loader import DataLoader


async def main():
    print("=" * 80)
    print("QUICK TITANIC TEST - Survived 타겟으로 Binary Classification")
    print("=" * 80)

    # 1. 데이터 업로드
    data_path = Path("data/titanic/train.csv")
    if not data_path.exists():
        print(f"❌ 데이터 파일 없음: {data_path}")
        return

    with open(data_path, 'rb') as f:
        file_content = f.read()

    file_info = FileManager.save_upload(file_content, data_path.name)
    file_id = file_info["file_id"]
    saved_path = file_info["saved_path"]

    print(f"✅ 파일 업로드: {file_id}")

    # 2. 세션 생성
    session_id = str(uuid.uuid4())
    session_store = get_session_store()
    session_store.create_session(session_id, initial_data={"file_id": file_id})

    # 3. Context 생성 - 타겟 컬럼 직접 지정
    context = AgentContext(
        session_id=session_id,
        data={
            "file_id": file_id,
            "file_path": saved_path,
            # Problem Definition을 미리 설정 (LLM 오감지 방지)
            "problem_definition": {
                "file_id": file_id,
                "file_path": saved_path,
                "target_column": "Survived",  # 올바른 타겟 지정!
                "problem_type": "binary_classification",
                "evaluation_metric": "roc_auc",
                "analysis_goal": "Predict Titanic passenger survival",
                "confidence": 1.0
            }
        },
        history=[]
    )

    print(f"✅ 세션 생성: {session_id}")
    print(f"✅ 타겟 컬럼: Survived (Binary Classification)")

    # 4. Orchestrator 실행 (Problem Definition 건너뛰고 Modeling부터)
    llm_router = LLMRouter()
    orchestrator = OrchestratorAgent(context=context, llm_provider=llm_router)

    # Modeling 단계만 실행
    print("\n⚙️  Modeling 단계 시작...")
    print("   예상 소요: 5-10분")

    start_time = datetime.now()

    try:
        # Modeling 단계만 실행
        from app.agents.modeling import ModelingAgent
        modeling_agent = ModelingAgent(context, llm_router)
        result = await modeling_agent.execute()

        duration = (datetime.now() - start_time).total_seconds()

        if result.success:
            print(f"\n✅ Modeling 성공! (소요: {duration:.1f}초)")

            # 결과 출력 (최상위 레벨에서 읽기)
            metrics = result.data.get("metrics", {})

            print("\n📊 모델 성능:")
            print(f"   - Best Estimator: {result.data.get('best_estimator')}")
            print(f"   - Run ID: {result.data.get('mlflow_run_id')}")
            print(f"   - Model Path: {result.data.get('model_path')}")
            print(f"   - Training Time: {result.data.get('training_time', 0):.1f}초")
            print(f"   - Metrics:")
            for k, v in metrics.items():
                if isinstance(v, float):
                    print(f"     * {k}: {v:.4f}")

            print(f"\n🎉 테스트 성공! 모델이 정상적으로 학습되었습니다.")
        else:
            print(f"\n❌ Modeling 실패: {result.error}")

    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
