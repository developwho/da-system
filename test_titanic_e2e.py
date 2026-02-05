"""
Titanic E2E Test - DA System 전체 워크플로우 검증
데이터 로딩 → 프로파일링 → 타입 감지 → AutoML 학습 → 평가
"""
import sys
import time
from pathlib import Path
import pandas as pd

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.data_pipeline.loader import DataLoader
from app.core.data_pipeline.validator import DataValidator
from app.core.data_pipeline.type_detector import TypeDetector
from app.core.data_pipeline.profiler import DataProfiler
from app.core.automl.flaml_wrapper import FLAMLWrapper
from app.storage.mlflow_tracker import MLflowTracker

print("=" * 80)
print("TITANIC E2E TEST - DA System")
print("=" * 80)

# ============================================================================
# Phase 1: 데이터 로딩 및 검증
# ============================================================================
print("\n[Phase 1] 데이터 로딩 및 검증")
print("-" * 80)

data_path = Path("data/titanic/train.csv")
print(f"Loading data from: {data_path}")

loader = DataLoader()
df, metadata = loader.load_file(data_path)
print(f"OK Loaded {len(df)} rows, {len(df.columns)} columns")
print(f"  Metadata: {metadata.get('file_id', 'N/A')[:8]}... ({metadata.get('file_size_mb', 0):.2f} MB)")

validator = DataValidator()
validation = validator.validate(df)
print(f"OK Validation: {'PASS' if validation['is_valid'] else 'FAIL'}")
if validation['errors']:
    print(f"  Errors: {validation['errors']}")
if validation['warnings']:
    print(f"  Warnings: {validation['warnings'][:3]}")  # First 3 warnings

# ============================================================================
# Phase 2: 타입 감지
# ============================================================================
print("\n[Phase 2] 문제 유형 자동 감지")
print("-" * 80)

type_detector = TypeDetector()
# Use detect_task_type with explicit target column
problem_type_info = type_detector.detect_task_type(
    df=df,
    target_column="Survived"
)

print(f"OK Task Type: {problem_type_info['task_type']}")
print(f"  Confidence: {problem_type_info.get('confidence', 0):.2%}")
print(f"  Reasoning: {problem_type_info.get('reasoning', 'N/A')}")
if 'details' in problem_type_info:
    details = problem_type_info['details']
    if 'unique_values' in details:
        print(f"  Unique Values: {details['unique_values']}")
    if 'class_distribution' in details:
        print(f"  Classes: {details['class_distribution']}")

# ============================================================================
# Phase 3: 데이터 프로파일링
# ============================================================================
print("\n[Phase 3] 데이터 프로파일링")
print("-" * 80)

profiler = DataProfiler()
profile = profiler.profile(df=df)

overview = profile['overview']
print(f"OK Profile Summary:")
print(f"  Total Observations: {overview['n_observations']}")
print(f"  Total Variables: {overview['n_variables']}")
print(f"  Missing Cells: {overview['missing_cells_pct']:.2f}%")
print(f"  Duplicate Rows: {overview['duplicate_rows']} ({overview['duplicate_rows_pct']:.2f}%)")
print(f"  Memory: {overview['memory_size_bytes'] / 1024 / 1024:.2f} MB")

# Variable types
print(f"\n  Variable Types:")
print(f"    Numeric: {overview['numeric_columns']}")
print(f"    Categorical: {overview['categorical_columns']}")
print(f"    DateTime: {overview['datetime_columns']}")

# High correlations
if 'correlations' in profile and 'high_correlations' in profile['correlations']:
    high_corrs = profile['correlations']['high_correlations']
    if high_corrs:
        print(f"\n  High Correlations (|r| > 0.7):")
        for pair in high_corrs[:3]:  # Top 3
            print(f"    {pair['var1']} <-> {pair['var2']}: {pair['correlation']:.3f}")

# ============================================================================
# Phase 4: 데이터 전처리
# ============================================================================
print("\n[Phase 4] 데이터 전처리")
print("-" * 80)

# Drop unnecessary columns
df_clean = df.drop(['PassengerId', 'Name', 'Ticket', 'Cabin'], axis=1)
print(f"OK Dropped ID/text columns: {len(df.columns)} -> {len(df_clean.columns)}")

# Fill missing values
df_clean['Age'] = df_clean['Age'].fillna(df_clean['Age'].median())
df_clean['Embarked'] = df_clean['Embarked'].fillna(df_clean['Embarked'].mode()[0])
print(f"OK Filled missing values in Age, Embarked")

# Encode categorical
df_clean['Sex'] = df_clean['Sex'].map({'male': 0, 'female': 1})
df_clean = pd.get_dummies(df_clean, columns=['Embarked'], drop_first=True)
print(f"OK Encoded categorical: Sex, Embarked")
print(f"  Final shape: {df_clean.shape}")

# Split features and target
X = df_clean.drop('Survived', axis=1)
y = df_clean['Survived']
print(f"\nOK Split X ({X.shape}) and y ({y.shape})")

# ============================================================================
# Phase 5: AutoML 학습 (FLAML)
# ============================================================================
print("\n[Phase 5] AutoML 학습 (FLAML)")
print("-" * 80)

# Initialize FLAML
flaml_config = {
    "task_type": "binary_classification",
    "time_budget": 60,  # 1 minute
    "metric": "roc_auc",
    "estimator_list": ["lgbm", "xgboost", "rf", "extra_tree"]
}

flaml = FLAMLWrapper(config=flaml_config)

print(f"Configuration:")
print(f"  Task: {flaml_config['task_type']}")
print(f"  Metric: {flaml_config['metric']}")
print(f"  Time Budget: {flaml_config['time_budget']}s")
print(f"  Estimators: {flaml_config['estimator_list']}")

print(f"\n[*] Training... (this may take ~60 seconds)")
start_time = time.time()

try:
    train_result = flaml.train(X, y)
    elapsed = time.time() - start_time
    print(f"OK Training completed in {elapsed:.1f}s")

    # Get best model info from train result
    print(f"\nOK Best Model:")
    print(f"  Estimator: {train_result.get('best_estimator', 'N/A')}")
    print(f"  Training Duration: {train_result.get('training_duration', 0):.1f}s")

    # Get feature importance from train result
    importance = train_result.get('feature_importance', {})
    if importance:
        print(f"\n  Top 5 Important Features:")
        for i, (feat, imp) in enumerate(list(importance.items())[:5], 1):
            print(f"    {i}. {feat}: {imp:.4f}")

except Exception as e:
    print(f"[X] Training failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# Phase 6: 모델 평가
# ============================================================================
print("\n[Phase 6] 모델 평가")
print("-" * 80)

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

    # Split for evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {X_train.shape}, Test: {X_test.shape}")

    # Predict
    y_pred = flaml.predict(X_test)
    y_pred_proba = flaml.predict_proba(X_test)

    # Metrics
    acc = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])

    print(f"\nOK Evaluation Results:")
    print(f"  Accuracy: {acc:.4f}")
    print(f"  ROC-AUC: {roc_auc:.4f}")

    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Died', 'Survived']))

except Exception as e:
    print(f"✗ Evaluation failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# Phase 7: 모델 저장
# ============================================================================
print("\n[Phase 7] 모델 저장")
print("-" * 80)

try:
    from pathlib import Path
    import joblib

    output_dir = Path("outputs/models/titanic_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "model.pkl"
    flaml.save_model(str(model_path))
    print(f"OK Model saved to: {model_path}")

    # Save metadata
    metadata = {
        'dataset': 'titanic',
        'task': flaml.task_type,
        'best_estimator': train_result.get('best_estimator'),
        'accuracy': acc,
        'roc_auc': roc_auc,
        'training_time': elapsed,
        'features': list(X.columns)
    }

    import json
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"OK Metadata saved to: {metadata_path}")

except Exception as e:
    print(f"✗ Save failed: {e}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"OK Data Loading: {len(df)} rows loaded")
print(f"OK Type Detection: {problem_type_info['task_type']}")
print(f"OK Preprocessing: {df_clean.shape} final shape")
print(f"OK AutoML Training: {elapsed:.1f}s")
print(f"OK Best Model: {train_result.get('best_estimator', 'N/A')}")
print(f"OK Performance: Accuracy={acc:.4f}, ROC-AUC={roc_auc:.4f}")
print(f"OK Model Saved: {model_path}")
print("\n*** E2E Test Completed Successfully! ***")
print("=" * 80)
