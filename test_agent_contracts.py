"""
Agent contract normalization smoke tests.
Run: python test_agent_contracts.py
"""
from app.agents.contracts import (
    normalize_problem_definition,
    normalize_research_results,
    normalize_modeling_result,
    normalize_insights_result,
)


def test_problem_definition_normalization():
    raw = {"goal": "predict churn", "target_variable": "churn"}
    normalized = normalize_problem_definition(raw)
    assert normalized["analysis_goal"] == "predict churn"
    assert normalized["target_column"] == "churn"


def test_research_results_normalization():
    raw = {
        "integrated_data": {
            "papers": [{"title": "Paper"}],
            "kaggle_solutions": {"competition": {"title": "Comp"}},
            "deep_research": {"summary": "Deep summary", "recommendations": ["xgb"]},
            "techniques": ["stacking"],
            "recommended_models": [],
            "key_insights": ["insight-1"],
        },
        "summary": "overall summary",
        "summary_file": "summary.md",
    }
    normalized = normalize_research_results(raw)
    assert normalized["papers"]
    assert normalized["kaggle_solutions"].get("competition", {}).get("title") == "Comp"
    assert normalized["deep_research"].get("summary") == "Deep summary"
    assert "stacking" in normalized["techniques"]
    assert "xgb" in normalized["recommended_models"]
    assert normalized["summary"] == "overall summary"


def test_modeling_result_normalization():
    raw = {
        "best_estimator": "xgboost",
        "metrics": {"roc_auc": 0.9},
        "model_data": {"feature_names": ["a", "b"]},
    }
    normalized = normalize_modeling_result(raw)
    assert normalized["best_estimator"] == "xgboost"
    assert normalized["metrics"]["roc_auc"] == 0.9
    assert normalized["feature_names"] == ["a", "b"]


def test_insights_result_normalization():
    raw = {
        "shap_results": {"top_features": [{"feature": "a", "importance": 0.5}]},
        "error_analysis": {"error_rate": 0.1},
        "insights": {"key_findings": ["kf1"], "recommendations": ["rec1"]},
    }
    normalized = normalize_insights_result(raw)
    assert normalized["key_findings"] == ["kf1"]
    assert normalized["recommendations"] == ["rec1"]
    assert normalized["shap_summary"][0]["feature"] == "a"
    assert normalized["error_summary"]["error_rate"] == 0.1


def main():
    test_problem_definition_normalization()
    test_research_results_normalization()
    test_modeling_result_normalization()
    test_insights_result_normalization()
    print("✅ Agent contract normalization tests passed")


if __name__ == "__main__":
    main()
