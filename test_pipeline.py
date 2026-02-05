"""
데이터 파이프라인 간단 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.core.data_pipeline.loader import DataLoader
from app.core.data_pipeline.validator import DataValidator
from app.core.data_pipeline.type_detector import TypeDetector
from app.core.data_pipeline.profiler import DataProfiler


def main():
    print("=" * 60)
    print("데이터 파이프라인 테스트")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n[1] 데이터 로딩...")
    data_path = "data/train.csv"
    df, metadata = DataLoader.load_file(data_path)
    print(f"[OK] 로드 완료: {metadata['n_rows']} 행 x {metadata['n_columns']} 열")
    print(f"     파일 ID: {metadata['file_id']}")
    print(f"     메모리 사용: {metadata['memory_usage_bytes'] / 1024 / 1024:.2f} MB")

    # 2. 데이터 검증
    print("\n[2] 데이터 검증...")
    validation = DataValidator.validate(df, target_column="target")
    print(f"[OK] 검증 결과: {'통과' if validation['is_valid'] else '실패'}")
    if validation['errors']:
        print(f"     에러: {validation['errors']}")
    if validation['warnings']:
        print(f"     경고: {len(validation['warnings'])}개")
    print(f"     결측치: {validation['summary']['missing_values']}개")
    print(f"     중복 행: {validation['summary']['duplicate_rows']}개")

    # 3. 타겟 변수 분석
    print("\n[3] 타겟 변수 분석...")
    target_analysis = DataValidator.check_target_variable(df, "target")
    print(f"[OK] 타겟 변수: {target_analysis['name']}")
    print(f"     타입: {target_analysis['type']}")
    print(f"     고유값: {target_analysis['nunique']}개")
    if 'value_counts' in target_analysis:
        print(f"     분포: {target_analysis['value_counts']}")

    # 4. 문제 유형 감지
    print("\n[4] 문제 유형 감지...")
    task_detection = TypeDetector.detect_task_type(df, "target")
    print(f"[OK] 감지된 태스크: {task_detection['task_type']}")
    print(f"     신뢰도: {task_detection['confidence']}")
    print(f"     이유: {task_detection['reasoning']}")
    if 'n_classes' in task_detection['details']:
        print(f"     클래스 수: {task_detection['details']['n_classes']}")
        print(f"     균형 여부: {task_detection['details']['is_balanced']}")

    # 5. 추천 메트릭
    metrics = TypeDetector.suggest_metrics(task_detection['task_type'])
    print(f"     추천 메트릭: {', '.join(metrics)}")

    # 6. 데이터 프로파일링 (간단 요약)
    print("\n[5] 데이터 프로파일링...")
    summary = DataProfiler.quick_summary(df)
    print(summary)

    # 7. 상세 프로파일 (일부만)
    print("\n[6] 변수 분석 (처음 5개)...")
    profile = DataProfiler.profile(df)
    var_names = list(profile['variables'].keys())[:5]
    for var_name in var_names:
        var_info = profile['variables'][var_name]
        print(f"  - {var_name}: {var_info['variable_type']}, "
              f"결측 {var_info['missing_pct']:.1f}%, "
              f"고유값 {var_info['unique_count']}개")

    print("\n" + "=" * 60)
    print("[OK] 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
