"""
Phase 2 통합 테스트
MLflow, FLAML, Celery 연동 테스트
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.core.automl.flaml_wrapper import FLAMLWrapper
from app.storage.mlflow_tracker import MLflowTracker
from app.utils.logger import get_logger

logger = get_logger(__name__)


def test_flaml_basic():
    """FLAML 기본 기능 테스트"""
    print("\n" + "="*60)
    print("TEST 1: FLAML Basic Training")
    print("="*60)

    try:
        # 간단한 테스트 데이터 생성
        np.random.seed(42)
        n_samples = 1000

        X = pd.DataFrame({
            'feature1': np.random.randn(n_samples),
            'feature2': np.random.randn(n_samples),
            'feature3': np.random.randint(0, 5, n_samples),
            'feature4': np.random.randn(n_samples) * 10
        })

        # 타겟 변수 (binary classification)
        y = pd.Series((X['feature1'] + X['feature2'] > 0).astype(int))

        print(f"Training data: {X.shape[0]} rows, {X.shape[1]} features")
        print(f"Target distribution: {y.value_counts().to_dict()}")

        # FLAML 학습
        config = {
            "task_type": "binary_classification",
            "time_budget": 30,  # 30초만 학습
            "metric": "roc_auc"
        }

        flaml = FLAMLWrapper(config)
        result = flaml.train(X, y)

        print(f"\n[OK] Training completed!")
        print(f"Best estimator: {result['best_estimator']}")
        print(f"Training duration: {result['training_duration']:.2f}s")
        print(f"Metrics:")
        for metric, value in result['metrics'].items():
            print(f"  - {metric}: {value:.4f}")

        # 예측 테스트
        predictions = flaml.predict(X.head(5))
        print(f"\nSample predictions: {predictions}")

        # Feature Importance
        print(f"\nTop 3 important features:")
        importance = result['feature_importance']
        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
        for feat, imp in sorted_features:
            print(f"  - {feat}: {imp:.4f}")

        return flaml, result

    except Exception as e:
        print(f"\n[ERROR] FLAML test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_mlflow_tracking(flaml, result):
    """MLflow 추적 테스트"""
    print("\n" + "="*60)
    print("TEST 2: MLflow Experiment Tracking")
    print("="*60)

    if flaml is None or result is None:
        print("[SKIP] Skipping MLflow test due to FLAML failure")
        return None

    try:
        # MLflow Tracker 생성
        tracker = MLflowTracker()
        print(f"[OK] MLflow tracker initialized")
        print(f"Tracking URI: {tracker.tracking_uri}")

        # 실험 로깅
        experiment_name = "test_phase2"
        run_id = tracker.log_experiment(
            experiment_name=experiment_name,
            params=flaml.get_params(),
            metrics=result["metrics"],
            model=flaml.model,
            tags={
                "test": "phase2",
                "estimator": result["best_estimator"]
            }
        )

        print(f"\n[OK] Experiment logged!")
        print(f"Run ID: {run_id}")

        # Run 조회
        run = tracker.get_run(run_id)
        print(f"\nRun info:")
        print(f"  - Status: {run.info.status}")
        print(f"  - Start time: {run.info.start_time}")

        # Best run 조회
        best_run = tracker.get_best_run(experiment_name, metric="roc_auc")
        if best_run:
            print(f"\nBest run:")
            print(f"  - Run ID: {best_run.info.run_id}")
            print(f"  - ROC-AUC: {best_run.data.metrics.get('roc_auc', 'N/A'):.4f}")

        print(f"\n[OK] You can view the experiment in MLflow UI:")
        print(f"     mlflow ui --backend-store-uri {tracker.tracking_uri}")

        return run_id

    except Exception as e:
        print(f"\n[ERROR] MLflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_model_save_load(flaml):
    """모델 저장/로드 테스트"""
    print("\n" + "="*60)
    print("TEST 3: Model Save/Load")
    print("="*60)

    if flaml is None:
        print("[SKIP] Skipping save/load test due to FLAML failure")
        return

    try:
        # 모델 저장
        save_path = "outputs/models/test_phase2"
        model_id = flaml.save_model(save_path)
        print(f"[OK] Model saved to: {model_id}")

        # 모델 로드
        loaded_flaml = FLAMLWrapper.load_model(save_path)
        print(f"[OK] Model loaded from: {save_path}")

        # 로드된 모델로 예측
        test_data = pd.DataFrame({
            'feature1': [0.5, -0.5],
            'feature2': [1.0, -1.0],
            'feature3': [2, 3],
            'feature4': [5.0, -5.0]
        })

        predictions = loaded_flaml.predict(test_data)
        print(f"[OK] Predictions with loaded model: {predictions}")

    except Exception as e:
        print(f"\n[ERROR] Save/load test failed: {e}")
        import traceback
        traceback.print_exc()


def test_redis_connection():
    """Redis 연결 테스트"""
    print("\n" + "="*60)
    print("TEST 4: Redis Connection")
    print("="*60)

    try:
        import redis
        from app.config import settings

        # Redis URL 파싱
        redis_url = settings.REDIS_URL
        print(f"Connecting to: {redis_url}")

        r = redis.from_url(redis_url)
        r.ping()

        print("[OK] Redis connection successful!")

        # 테스트 데이터 저장/조회
        r.set("test_key", "test_value")
        value = r.get("test_key")
        print(f"[OK] Test key-value: {value.decode('utf-8')}")
        r.delete("test_key")

        return True

    except Exception as e:
        print(f"\n[ERROR] Redis connection failed: {e}")
        print("Make sure Redis is running:")
        print("  - Windows: Install Redis or use Docker")
        print("  - Docker: docker run -d -p 6379:6379 redis")
        return False


def test_celery_worker():
    """Celery Worker 상태 테스트"""
    print("\n" + "="*60)
    print("TEST 5: Celery Worker Status")
    print("="*60)

    try:
        from app.tasks.celery_app import celery_app

        # Worker 상태 조회
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            print("[OK] Celery workers are running!")
            for worker, stat in stats.items():
                print(f"\nWorker: {worker}")
                print(f"  - Pool: {stat.get('pool', {}).get('implementation')}")
                print(f"  - Max concurrency: {stat.get('pool', {}).get('max-concurrency')}")
        else:
            print("[WARNING] No Celery workers found!")
            print("Start a worker with:")
            print("  celery -A app.tasks.celery_app worker --loglevel=info --pool=solo")

        # 등록된 태스크 조회
        registered = inspect.registered()
        if registered:
            print("\nRegistered tasks:")
            for worker, tasks in registered.items():
                for task in tasks:
                    if "app.tasks" in task:
                        print(f"  - {task}")

    except Exception as e:
        print(f"\n[ERROR] Celery check failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("PHASE 2 INTEGRATION TEST")
    print("="*60)

    # 1. FLAML 테스트
    flaml, result = test_flaml_basic()

    # 2. MLflow 테스트
    run_id = test_mlflow_tracking(flaml, result)

    # 3. 모델 저장/로드 테스트
    test_model_save_load(flaml)

    # 4. Redis 연결 테스트
    redis_ok = test_redis_connection()

    # 5. Celery Worker 테스트
    if redis_ok:
        test_celery_worker()
    else:
        print("\n[SKIP] Skipping Celery test due to Redis failure")

    # 요약
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("[OK] FLAML wrapper: Working" if flaml else "[ERROR] FLAML wrapper: Failed")
    print("[OK] MLflow tracking: Working" if run_id else "[ERROR] MLflow tracking: Failed")
    print("[OK] Redis: Working" if redis_ok else "[ERROR] Redis: Not running")
    print("\nNext steps:")
    print("1. Start Redis if not running")
    print("2. Start Celery worker:")
    print("   celery -A app.tasks.celery_app worker --loglevel=info --pool=solo")
    print("3. Start FastAPI server:")
    print("   python -m uvicorn app.main:app --reload")
    print("4. Test the /api/v1/analysis/train endpoint")
    print("\nPhase 2 components are ready for integration testing!")


if __name__ == "__main__":
    main()
